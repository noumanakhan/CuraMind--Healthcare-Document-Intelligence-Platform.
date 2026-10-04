import pytest
from app.db import postgres as db
from app.services.embeddings import get_embedding_provider
from app.services.ingestion import chunk_text, process_document_background
from app.services.retrieval import search_chunks
from app.core.rbac import AuthenticatedUser


@pytest.mark.anyio
async def test_chunking_fidelity_and_page_numbers():
    long_text_page1 = "Page 1 start. " + "Clinical progress note entry. " * 30 + "Page 1 end."
    long_text_page2 = "Page 2 start. " + "Assessment and treatment plan. " * 30 + "Page 2 end."
    pages_data = [
        {"page_number": 1, "text": long_text_page1},
        {"page_number": 2, "text": long_text_page2},
    ]

    chunks = chunk_text(pages_data, chunk_size=300, chunk_overlap=30)
    assert len(chunks) > 2

    # Check page numbers are preserved
    p1_chunks = [c for c in chunks if c["page_number"] == 1]
    p2_chunks = [c for c in chunks if c["page_number"] == 2]
    assert len(p1_chunks) > 0
    assert len(p2_chunks) > 0

    # Verify embeddings dimensionality
    embedding_provider = get_embedding_provider()
    embeddings = embedding_provider.embed_batch([c["chunk_text"] for c in chunks])
    assert len(embeddings) == len(chunks)
    for emb in embeddings:
        assert len(emb) == 1536
        assert any(x != 0.0 for x in emb)


@pytest.mark.anyio
async def test_soft_deleting_document_excludes_chunks_from_retrieval():
    ws_id = "ws-test-del"
    p_id = "pat-1"
    doc_id = "doc-to-delete"
    user = AuthenticatedUser(id="u1", workspace_id=ws_id, role="clinician")

    # 1. Ingest document
    await db.insert_document({
        "id": doc_id,
        "workspace_id": ws_id,
        "patient_id": p_id,
        "name": "Echocardiogram Report",
        "type": "clinical_note",
        "status": "processing"
    })
    await process_document_background(
        doc_id=doc_id,
        workspace_id=ws_id,
        patient_id=p_id,
        file_bytes=b"Echocardiogram reveals left ventricular ejection fraction of 55%. Normal valves.",
        filename="Echocardiogram Report.txt",
        user_id=user.id,
    )

    # 2. Search before deletion: chunk should be found
    provider = get_embedding_provider()
    q_emb = provider.embed_text("ejection fraction echocardiogram")
    results = await search_chunks(q_emb, workspace_id=ws_id, user=user, patient_id=p_id)
    assert len(results) > 0
    assert results[0]["document_id"] == doc_id

    # 3. Soft-delete the document
    await db.soft_delete_document(doc_id, workspace_id=ws_id)

    # 4. Search after deletion: must return 0 results
    results_after = await search_chunks(q_emb, workspace_id=ws_id, user=user, patient_id=p_id)
    assert len(results_after) == 0
