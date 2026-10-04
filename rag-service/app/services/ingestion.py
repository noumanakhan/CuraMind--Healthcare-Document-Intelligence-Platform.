import io
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple
from pypdf import PdfReader
import docx

from app.db import postgres as db
from app.services.embeddings import get_embedding_provider
from app.services.ocr import get_ocr_provider

logger = logging.getLogger("rag_service.ingestion")


def extract_text_from_pdf(file_bytes: bytes, filename: Optional[str] = None) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Extracts text from PDF bytes.
    Returns (full_text, pages_data) where pages_data is list of {page_num, text}.
    If pages have no text layer, triggers OCR provider.
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        full_text_parts = []
        pages_data = []
        ocr_provider = get_ocr_provider()

        for idx, page in enumerate(reader.pages, start=1):
            page_text = (page.extract_text() or "").strip()
            if not page_text:
                page_text = ocr_provider.extract_text_from_image(file_bytes, filename=f"{filename or 'doc'}_page_{idx}.png")
            if page_text:
                full_text_parts.append(f"--- Page {idx} ---\n{page_text}")
                pages_data.append({"page_number": idx, "text": page_text})

        if full_text_parts:
            return "\n\n".join(full_text_parts), pages_data
    except Exception:
        pass

    # Fallback to UTF-8 decoding or OCR
    try:
        text = file_bytes.decode("utf-8")
        if text.strip():
            return text, [{"page_number": 1, "text": text}]
    except Exception:
        pass

    ocr_text = get_ocr_provider().extract_text_from_image(file_bytes, filename)
    return ocr_text, [{"page_number": 1, "text": ocr_text}]


def extract_text_from_docx(file_bytes: bytes) -> Tuple[str, List[Dict[str, Any]]]:
    """Extracts text from DOCX document."""
    doc = docx.Document(io.BytesIO(file_bytes))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    full_text = "\n\n".join(paragraphs)
    pages_data = [{"page_number": 1, "text": full_text}]
    return full_text, pages_data


def extract_text_from_raw(file_bytes: bytes, filename: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Auto-detects file type and extracts full text and page/section breakdowns."""
    lower_name = filename.lower()
    if lower_name.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes, filename)
    elif lower_name.endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    elif any(lower_name.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]):
        text = get_ocr_provider().extract_text_from_image(file_bytes, filename)
        return text, [{"page_number": 1, "text": text}]
    else:
        # Assume plain text / UTF-8
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1", errors="replace")
        return text, [{"page_number": 1, "text": text}]


def chunk_text(
    pages_data: List[Dict[str, Any]],
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> List[Dict[str, Any]]:
    """
    Splits text across pages into overlapping chunks while preserving page numbers.
    """
    chunks = []
    chunk_index = 0

    for page_item in pages_data:
        page_num = page_item.get("page_number", 1)
        text = page_item["text"]

        if len(text) <= chunk_size:
            if text.strip():
                chunks.append({
                    "chunk_text": text.strip(),
                    "page_number": page_num,
                    "chunk_index": chunk_index,
                })
                chunk_index += 1
            continue

        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_slice = text[start:end].strip()
            if chunk_slice:
                chunks.append({
                    "chunk_text": chunk_slice,
                    "page_number": page_num,
                    "chunk_index": chunk_index,
                })
                chunk_index += 1
            start += (chunk_size - chunk_overlap)

    return chunks


async def process_document_background(
    doc_id: str,
    workspace_id: str,
    patient_id: str,
    file_bytes: bytes,
    filename: str,
    user_id: str,
    user_email: Optional[str] = None
):
    """
    Asynchronous background worker for OCR, full-text extraction, chunking, and embedding generation.
    Catches any parsing error and sets processing_status='failed' with processing_error.
    """
    try:
        logger.info(f"Starting background ingestion for document {doc_id} ({filename})")
        full_text, pages_data = extract_text_from_raw(file_bytes, filename)

        if not full_text.strip():
            raise ValueError("No extractable text or content found in document")

        # 1. Update Document with full text
        await db.update_document(doc_id, {
            "full_text": full_text,
            "status": "processing",
            "processing_error": None
        })

        # 2. Generate chunks
        raw_chunks = chunk_text(pages_data, chunk_size=500, chunk_overlap=50)
        if not raw_chunks:
            raw_chunks = [{"chunk_text": full_text[:500], "page_number": 1, "chunk_index": 0}]

        # 3. Batch generate embeddings
        embedding_provider = get_embedding_provider()
        texts = [c["chunk_text"] for c in raw_chunks]
        embeddings = embedding_provider.embed_batch(texts)

        # 4. Prepare chunk records for pure PostgreSQL insertion
        chunk_records = []
        for idx, (c, emb) in enumerate(zip(raw_chunks, embeddings)):
            chunk_records.append({
                "id": str(uuid.uuid4()),
                "document_id": doc_id,
                "workspace_id": workspace_id,
                "patient_id": patient_id,
                "chunk_text": c["chunk_text"],
                "page_number": c["page_number"],
                "chunk_index": idx,
                "embedding": emb,
            })

        await db.insert_chunks(chunk_records)

        # 5. Mark document as processed
        await db.update_document(doc_id, {
            "status": "processed",
            "processing_error": None
        })

        # 6. Record audit event
        await db.log_audit({
            "workspace_id": workspace_id,
            "user_id": user_id,
            "user_email": user_email,
            "patient_id": patient_id,
            "action": "document.processed",
            "detail": f"Document '{filename}' ({doc_id}) processed into {len(chunk_records)} vector chunks.",
        })
        logger.info(f"Successfully processed document {doc_id} into {len(chunk_records)} chunks.")

    except Exception as e:
        logger.error(f"Document ingestion failed for {doc_id}: {e}", exc_info=True)
        await db.update_document(doc_id, {
            "status": "failed",
            "processing_error": f"Text extraction / ingestion error: {str(e)}"
        })
        await db.log_audit({
            "workspace_id": workspace_id,
            "user_id": user_id,
            "user_email": user_email,
            "patient_id": patient_id,
            "action": "document.failed",
            "detail": f"Failed to ingest document '{filename}': {str(e)}",
        })
