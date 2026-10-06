import io
import pytest
from docx import Document
from app.services.ingestion import (
    chunk_text,
    extract_text_from_pdf,
    extract_text_from_raw,
    process_document_background,
)
from app.db import postgres as db
from tests.conftest import auth_header, make_token


def create_sample_pdf(text: str = "Patient Jane Doe presented with severe cough and fever. Vital signs: BP 120/80.") -> bytes:
    # Use pypdf to create an in-memory PDF
    from pypdf import PdfWriter
    writer = PdfWriter()
    # Add a blank page with text annotation or create a valid minimal PDF
    # Or create a minimal valid PDF byte stream
    writer.add_blank_page(width=612, height=792)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


@pytest.mark.anyio
async def test_text_and_ocr_extraction():
    # 1. Plain text extraction
    raw_text = b"Patient admitted with acute bacterial pneumonia. Prescribed Azithromycin 500mg daily."
    extracted, pages = extract_text_from_raw(raw_text, "report.txt")
    assert "pneumonia" in extracted
    assert len(pages) == 1
    assert pages[0]["page_number"] == 1

    # Mock OCR must not invent clinical facts when no OCR engine is configured.
    image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    ocr_text, ocr_pages = extract_text_from_raw(image_bytes, "scanned_doc.png")
    assert ocr_text == ""
    assert ocr_pages == []
    assert "Azithromycin" not in ocr_text


def test_docx_langchain_loader_preserves_source_metadata():
    from app.services.ingestion import extract_text_from_docx

    doc = Document()
    doc.add_paragraph("The patient reports a penicillin allergy.")
    stream = io.BytesIO()
    doc.save(stream)

    text, pages = extract_text_from_docx(stream.getvalue())
    # The raw loader source points to a temp file; dispatch replaces it with the uploaded name.
    from app.services.ingestion import extract_text_from_raw
    loaded_text, loaded_pages = extract_text_from_raw(stream.getvalue(), "allergy-note.docx")
    assert "penicillin allergy" in text.lower()
    assert loaded_text == text
    assert loaded_pages[0]["page_number"] == 1
    assert loaded_pages[0]["metadata"]["source"] == "allergy-note.docx"


@pytest.mark.anyio
async def test_corrupted_file_handling_does_not_500():
    doc_id = "doc-corrupt-1"
    ws_id = "ws-1"
    p_id = "patient-1"

    # Create doc record
    await db.insert_document({
        "id": doc_id,
        "workspace_id": ws_id,
        "patient_id": p_id,
        "name": "empty_bad_file.pdf",
        "type": "clinical_note",
        "status": "processing"
    })

    # Run background ingestion on empty/invalid content
    await process_document_background(
        doc_id=doc_id,
        workspace_id=ws_id,
        patient_id=p_id,
        file_bytes=b"",
        filename="empty_bad_file.pdf",
        user_id="user-1",
    )

    # Document should be marked as 'failed' with reason, not crash the system
    doc = await db.get_document(doc_id, workspace_id=ws_id)
    assert doc is not None
    assert doc["status"] == "failed"
    assert doc["processing_error"] is not None


def test_upload_endpoint_returns_immediately(client):
    token = make_token("u-clinician", "ws-1", "clinician")
    files = {"file": ("intake_note.txt", b"Patient admitted for observation.", "text/plain")}
    data = {"patient_id": "p-100", "name": "Intake Note", "type": "intake_form"}

    res = client.post("/api/v1/documents/upload", files=files, data=data, headers=auth_header(token))
    assert res.status_code == 202
    res_json = res.json()
    assert res_json["status"] == "processing"
    assert res_json["patient_id"] == "p-100"
