import pytest
from app.core.rbac import AuthenticatedUser
from app.db import postgres as db
from app.services.embeddings import get_embedding_provider
from app.services.ingestion import process_document_background
from app.services.retrieval import CuraMindAuthorizedRetriever, search_chunks
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever


@pytest.mark.anyio
async def test_workspace_and_patient_retrieval_isolation():
    provider = get_embedding_provider()

    # Workspace 1, Patient A
    await db.insert_document({
        "id": "doc-ws1-pa",
        "workspace_id": "ws-1",
        "patient_id": "pat-A",
        "name": "Discharge Note Patient A",
        "type": "clinical_note",
    })
    await process_document_background(
        doc_id="doc-ws1-pa",
        workspace_id="ws-1",
        patient_id="pat-A",
        file_bytes=b"Patient A has diagnosed Type 2 Diabetes Mellitus managed on Metformin.",
        filename="doc-ws1-pa.txt",
        user_id="user-1",
    )

    # Workspace 1, Patient B
    await db.insert_document({
        "id": "doc-ws1-pb",
        "workspace_id": "ws-1",
        "patient_id": "pat-B",
        "name": "Discharge Note Patient B",
        "type": "clinical_note",
    })
    await process_document_background(
        doc_id="doc-ws1-pb",
        workspace_id="ws-1",
        patient_id="pat-B",
        file_bytes=b"Patient B has severe Penicillin anaphylaxis and asthma.",
        filename="doc-ws1-pb.txt",
        user_id="user-1",
    )

    # Workspace 2, Patient C
    await db.insert_document({
        "id": "doc-ws2-pc",
        "workspace_id": "ws-2",
        "patient_id": "pat-C",
        "name": "Note Patient C Hospital 2",
        "type": "clinical_note",
    })
    await process_document_background(
        doc_id="doc-ws2-pc",
        workspace_id="ws-2",
        patient_id="pat-C",
        file_bytes=b"Patient C secret medical records in Hospital Two with Diabetes.",
        filename="doc-ws2-pc.txt",
        user_id="user-2",
    )

    clinician_ws1 = AuthenticatedUser(id="u1", workspace_id="ws-1", role="clinician")
    clinician_ws2 = AuthenticatedUser(id="u2", workspace_id="ws-2", role="clinician")

    # 1. Query scoped to Patient A must NOT return Patient B's or Patient C's data
    q_emb = provider.embed_text("penicillin allergy or asthma or diabetes")
    res_pat_a = await search_chunks(q_emb, workspace_id="ws-1", user=clinician_ws1, patient_id="pat-A")
    assert len(res_pat_a) > 0
    for r in res_pat_a:
        assert r["patient_id"] == "pat-A"
        assert r["workspace_id"] == "ws-1"
        assert "Patient B" not in r["chunk_text"]
        assert "Hospital Two" not in r["chunk_text"]

    # 2. Query in Workspace 1 must NEVER return chunks from Workspace 2
    res_ws1_all = await search_chunks(q_emb, workspace_id="ws-1", user=clinician_ws1, patient_id=None)
    for r in res_ws1_all:
        assert r["workspace_id"] == "ws-1"
        assert r["document_id"] != "doc-ws2-pc"

    # 3. Viewer searching workspace-wide is restricted from clinical notes
    viewer_ws1 = AuthenticatedUser(id="u-viewer", workspace_id="ws-1", role="viewer")
    res_viewer = await search_chunks(q_emb, workspace_id="ws-1", user=viewer_ws1, patient_id=None)
    for r in res_viewer:
        assert r["document_type"] != "clinical_note"


@pytest.mark.anyio
async def test_hybrid_search_exact_keyword_and_semantic():
    ws_id = "ws-hybrid-test"
    p_id = "pat-hybrid-1"
    user = AuthenticatedUser(id="u1", workspace_id=ws_id, role="clinician")
    provider = get_embedding_provider()

    # Document 1 with specific dosage and drug name
    await db.insert_document({
        "id": "doc-h1",
        "workspace_id": ws_id,
        "patient_id": p_id,
        "name": "Medication Reconciliation",
        "type": "clinical_note",
    })
    await process_document_background(
        doc_id="doc-h1",
        workspace_id=ws_id,
        patient_id=p_id,
        file_bytes=b"Prescribed Lisinopril 20mg once daily oral for stage 2 hypertension. Code ICD-10 I10.",
        filename="Medication Reconciliation.txt",
        user_id="u1",
    )

    # Document 2 with general blood pressure discussion
    await db.insert_document({
        "id": "doc-h2",
        "workspace_id": ws_id,
        "patient_id": p_id,
        "name": "General Wellness Notes",
        "type": "clinical_note",
    })
    await process_document_background(
        doc_id="doc-h2",
        workspace_id=ws_id,
        patient_id=p_id,
        file_bytes=b"Patient advised to reduce sodium intake to assist with cardiovascular pressure control.",
        filename="General Wellness Notes.txt",
        user_id="u1",
    )

    # Test exact keyword search + semantic fusion: "Lisinopril 20mg ICD-10"
    query = "Lisinopril 20mg ICD-10"
    q_emb = provider.embed_text(query)

    results = await search_chunks(
        query_embedding=q_emb,
        workspace_id=ws_id,
        user=user,
        patient_id=p_id,
        query_text=query,
    )

    assert len(results) >= 1
    # Top result must be doc-h1 with exact keyword match
    top_hit = results[0]
    assert top_hit["document_id"] == "doc-h1"
    assert "Lisinopril 20mg" in top_hit["chunk_text"]
    assert "hybrid_score" in top_hit
    assert "sparse_score" in top_hit
    assert top_hit["sparse_score"] > 0


@pytest.mark.anyio
async def test_authorized_langchain_retriever_returns_provenance_metadata():
    workspace_id = "ws-lc-retriever"
    patient_id = "patient-lc-retriever"
    user = AuthenticatedUser(id="lc-user", workspace_id=workspace_id, role="clinician")
    await db.insert_document({
        "id": "doc-lc-retriever",
        "workspace_id": workspace_id,
        "patient_id": patient_id,
        "name": "Retriever Provenance Note",
        "type": "clinical_note",
        "source": "source-note.pdf",
    })
    await process_document_background(
        doc_id="doc-lc-retriever",
        workspace_id=workspace_id,
        patient_id=patient_id,
        file_bytes=b"The patient has a documented penicillin allergy.",
        filename="source-note.pdf",
        user_id=user.id,
    )

    retriever = CuraMindAuthorizedRetriever(user=user, patient_id=patient_id)
    assert isinstance(retriever, BaseRetriever)
    documents = await retriever.ainvoke("penicillin allergy")
    assert documents
    assert isinstance(documents[0], Document)
    assert documents[0].metadata["workspace_id"] == workspace_id
    assert documents[0].metadata["patient_id"] == patient_id
    assert documents[0].metadata["document_id"] == "doc-lc-retriever"
    assert documents[0].metadata["document_name"] == "Retriever Provenance Note"
    assert documents[0].metadata["page_number"] == 1
