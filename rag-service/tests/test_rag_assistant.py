import pytest
from app.core.rbac import AuthenticatedUser
from app.db import postgres as db
from app.services.ingestion import process_document_background
from app.services.rag_assistant import ask_rag_assistant


@pytest.mark.anyio
async def test_rag_assistant_grounded_answer_and_citations():
    ws_id = "ws-rag-1"
    pat_id = "pat-rag-1"
    user = AuthenticatedUser(id="u-dr1", workspace_id=ws_id, role="clinician", email="dr@hospital.org")

    # Ingest a clinical discharge document
    doc_id = "doc-rag-cardio"
    await db.insert_document({
        "id": doc_id,
        "workspace_id": ws_id,
        "patient_id": pat_id,
        "name": "Cardiology Consultation Note",
        "type": "clinical_note",
    })
    await process_document_background(
        doc_id=doc_id,
        workspace_id=ws_id,
        patient_id=pat_id,
        file_bytes=b"The patient has a known allergy to Penicillin. Prescribed daily dosage of Lisinopril 10mg.",
        filename="Cardiology Consultation Note.txt",
        user_id=user.id,
    )

    # Create conversation
    conv = await db.create_conversation({
        "workspace_id": ws_id,
        "patient_id": pat_id,
        "user_id": user.id,
        "title": "Allergy & Medication Check",
    })

    # 1. Ask question with known answer in the document
    reply = await ask_rag_assistant(
        conversation_id=conv["id"],
        user_query="What allergies and prescribed medications does this patient have?",
        user=user,
        patient_id=pat_id,
    )

    assert reply.role == "assistant"
    assert len(reply.citations) > 0
    assert reply.citations[0].document_name == "Cardiology Consultation Note"
    assert "Cardiology Consultation Note" in reply.content or "Penicillin" in reply.content or "Lisinopril" in reply.content
    assert reply.disclaimer is not None

    # 2. Ask conversational greeting -> Should return helpful clinical assistant welcome without refusal error
    reply_greeting = await ask_rag_assistant(
        conversation_id=conv["id"],
        user_query="hi",
        user=user,
        patient_id=pat_id,
    )
    assert reply_greeting.role == "assistant"
    assert "CuraMind" in reply_greeting.content or "Assistant" in reply_greeting.content
    assert "No relevant" not in reply_greeting.content

    # 3. Ask question with zero matching context (Out of domain query) -> Must refuse
    reply_unrelated = await ask_rag_assistant(
        conversation_id=conv["id"],
        user_query="What is the stock price of Apple Inc and did the patient travel to Mars?",
        user=user,
        patient_id=pat_id,
    )
    assert "No relevant" in reply_unrelated.content or "not found" in reply_unrelated.content


@pytest.mark.anyio
async def test_cross_patient_data_cannot_leak_through_rag():
    ws_id = "ws-rag-leak"
    u_clinician = AuthenticatedUser(id="u1", workspace_id=ws_id, role="clinician")

    # Ingest sensitive secret in Patient A's chart
    await db.insert_document({
        "id": "doc-pat-a",
        "workspace_id": ws_id,
        "patient_id": "pat-alpha",
        "name": "Secret Genetic Marker Patient A",
        "type": "clinical_note",
    })
    await process_document_background(
        doc_id="doc-pat-a",
        workspace_id=ws_id,
        patient_id="pat-alpha",
        file_bytes=b"SECRET_MARKER_999: Patient Alpha has rare BRCA1 mutation confirmed.",
        filename="Secret Genetic Marker.txt",
        user_id="u1",
    )

    # Ingest Patient B's chart
    await db.insert_document({
        "id": "doc-pat-b",
        "workspace_id": ws_id,
        "patient_id": "pat-beta",
        "name": "Routine Physical Patient B",
        "type": "clinical_note",
    })
    await process_document_background(
        doc_id="doc-pat-b",
        workspace_id=ws_id,
        patient_id="pat-beta",
        file_bytes=b"Patient Beta underwent routine checkup. Normal vision and hearing.",
        filename="Routine Physical.txt",
        user_id="u1",
    )

    # Create conversation scoped to Patient B
    conv_b = await db.create_conversation({
        "workspace_id": ws_id,
        "patient_id": "pat-beta",
        "user_id": "u1",
        "title": "Patient B Chat",
    })

    # Query asking about Secret Genetic Marker while in Patient B's conversation
    reply_b = await ask_rag_assistant(
        conversation_id=conv_b["id"],
        user_query="What is the SECRET_MARKER_999 BRCA1 mutation status?",
        user=u_clinician,
        patient_id="pat-beta",
    )

    # Must refuse and NOT reveal Patient A's secret
    assert "SECRET_MARKER_999" not in reply_b.content
    assert "BRCA1" not in reply_b.content
    for cite in reply_b.citations:
        assert cite.document_name != "Secret Genetic Marker Patient A"
