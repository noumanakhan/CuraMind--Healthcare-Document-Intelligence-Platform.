import pytest
from app.core.rbac import AuthenticatedUser
from app.db import postgres as db
from app.services.embeddings import get_embedding_provider
from app.services.ingestion import process_document_background
from app.services.retrieval import search_chunks


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
