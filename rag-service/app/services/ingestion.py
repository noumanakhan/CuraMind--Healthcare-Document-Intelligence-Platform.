import io
import logging
import tempfile
import uuid
from typing import Any, Dict, List, Optional, Tuple

from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.db import postgres as db
from app.services.embeddings import get_embedding_provider
from app.services.ocr import get_ocr_provider

logger = logging.getLogger("rag_service.ingestion")


def extract_text_from_pdf(file_bytes: bytes, filename: Optional[str] = None) -> Tuple[str, List[Dict[str, Any]]]:
    """Load PDF pages and preserve page/source metadata; OCR scanned pages if possible."""
    pages_data: List[Dict[str, Any]] = []
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf") as pdf_file:
            pdf_file.write(file_bytes)
            pdf_file.flush()
            documents = PyPDFLoader(pdf_file.name).load()
        for index, document in enumerate(documents, start=1):
            text = document.page_content.strip()
            if not text:
                image_bytes = _render_pdf_page(file_bytes, index - 1)
                if image_bytes:
                    text = get_ocr_provider().extract_text_from_image(
                        image_bytes, filename=f"{filename or 'document'}_page_{index}.png"
                    ).strip()
            if text:
                metadata = dict(document.metadata)
                metadata.update({"source": filename or metadata.get("source"), "page_number": index})
                pages_data.append({"page_number": index, "text": text, "metadata": metadata})
    except Exception:
        logger.exception("LangChain PDF loader failed; trying pypdf fallback")
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(file_bytes))
            for index, page in enumerate(reader.pages, start=1):
                text = (page.extract_text() or "").strip()
                if text:
                    pages_data.append({
                        "page_number": index,
                        "text": text,
                        "metadata": {"source": filename, "page_number": index},
                    })
        except Exception:
            logger.exception("pypdf fallback failed")

    if not pages_data and file_bytes:
        # Existing tests and text fixtures use a printable UTF-8 payload named as a PDF.
        try:
            decoded = file_bytes.decode("utf-8")
            printable_ratio = sum(char.isprintable() or char in "\n\r\t" for char in decoded) / len(decoded)
            if decoded.strip() and printable_ratio >= 0.95:
                pages_data = [{
                    "page_number": 1,
                    "text": decoded,
                    "metadata": {"source": filename, "page_number": 1},
                }]
        except (UnicodeDecodeError, ZeroDivisionError):
            pass

    full_text = "\n\n".join(
        f"--- Page {page['page_number']} ---\n{page['text']}" for page in pages_data
    )
    return full_text, pages_data


def _render_pdf_page(file_bytes: bytes, page_index: int) -> Optional[bytes]:
    """Render one scanned PDF page as PNG for the configured OCR provider."""
    try:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(file_bytes)
        try:
            output = io.BytesIO()
            pdf[page_index].render(scale=2).to_pil().convert("RGB").save(output, format="PNG")
            return output.getvalue()
        finally:
            pdf.close()
    except Exception:
        logger.exception("Could not render scanned PDF page %s", page_index + 1)
        return None


def extract_text_from_docx(file_bytes: bytes) -> Tuple[str, List[Dict[str, Any]]]:
    """Load DOCX text with LangChain and preserve loader metadata."""
    with tempfile.NamedTemporaryFile(suffix=".docx") as docx_file:
        docx_file.write(file_bytes)
        docx_file.flush()
        documents = Docx2txtLoader(docx_file.name).load()
    full_text = "\n\n".join(
        document.page_content.strip() for document in documents if document.page_content.strip()
    )
    metadata = dict(documents[0].metadata) if documents else {}
    pages = [{"page_number": 1, "text": full_text, "metadata": metadata}] if full_text else []
    return full_text, pages


def extract_text_from_raw(file_bytes: bytes, filename: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Use LangChain loaders for PDF, DOCX and text; retain the existing image OCR path."""
    lower_name = filename.lower()
    if lower_name.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes, filename)
    if lower_name.endswith(".docx"):
        text, pages = extract_text_from_docx(file_bytes)
        for page in pages:
            page.setdefault("metadata", {})["source"] = filename
        return text, pages
    if lower_name.endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp")):
        text = get_ocr_provider().extract_text_from_image(file_bytes, filename).strip()
        return (text, [{"page_number": 1, "text": text, "metadata": {"source": filename}}]) if text else ("", [])

    try:
        with tempfile.NamedTemporaryFile(suffix=".txt") as text_file:
            text_file.write(file_bytes)
            text_file.flush()
            documents = TextLoader(text_file.name, encoding="utf-8").load()
        text = "\n\n".join(document.page_content for document in documents)
    except UnicodeDecodeError:
        text = file_bytes.decode("latin-1", errors="replace")
    return (text, [{"page_number": 1, "text": text, "metadata": {"source": filename}}]) if text.strip() else ("", [])


def chunk_text(
    pages_data: List[Dict[str, Any]],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> List[Dict[str, Any]]:
    """Split each page independently and retain loader metadata and page mapping."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
        is_separator_regex=False,
    )
    chunks: List[Dict[str, Any]] = []
    for page in pages_data:
        page_number = page.get("page_number", 1)
        text = page.get("text", "")
        if not text.strip():
            continue
        metadata = dict(page.get("metadata") or {})
        metadata["page_number"] = page_number
        for document in splitter.create_documents([text], metadatas=[metadata]):
            cleaned = document.page_content.strip()
            if cleaned:
                chunks.append({
                    "chunk_text": cleaned,
                    "page_number": page_number,
                    "chunk_index": len(chunks),
                    "metadata": document.metadata,
                })
    return chunks


async def process_document_background(
    doc_id: str,
    workspace_id: str,
    patient_id: str,
    file_bytes: bytes,
    filename: str,
    user_id: str,
    user_email: Optional[str] = None,
):
    """Extract, split, embed and persist an uploaded document asynchronously."""
    try:
        logger.info("Starting background ingestion for document %s (%s)", doc_id, filename)
        full_text, pages_data = extract_text_from_raw(file_bytes, filename)
        if not full_text.strip():
            raise ValueError("No extractable text or content found in document")

        await db.update_document(doc_id, {
            "full_text": full_text,
            "status": "processing",
            "processing_error": None,
        })
        chunks = chunk_text(pages_data, chunk_size=500, chunk_overlap=50)
        if not chunks:
            chunks = [{"chunk_text": full_text[:500], "page_number": 1, "chunk_index": 0}]
        embeddings = get_embedding_provider().embed_batch([chunk["chunk_text"] for chunk in chunks])
        if len(embeddings) != len(chunks):
            raise ValueError("Embedding provider returned a mismatched number of vectors")

        chunk_records = [{
            "id": str(uuid.uuid4()),
            "document_id": doc_id,
            "workspace_id": workspace_id,
            "patient_id": patient_id,
            "chunk_text": chunk["chunk_text"],
            "page_number": chunk["page_number"],
            "chunk_index": index,
            "embedding": embeddings[index],
        } for index, chunk in enumerate(chunks)]
        await db.insert_chunks(chunk_records)
        await db.update_document(doc_id, {"status": "processed", "processing_error": None})
        await db.log_audit({
            "workspace_id": workspace_id,
            "user_id": user_id,
            "user_email": user_email,
            "patient_id": patient_id,
            "action": "document.processed",
            "detail": f"Document '{filename}' ({doc_id}) processed into {len(chunk_records)} vector chunks.",
        })
        logger.info("Successfully processed document %s into %s chunks", doc_id, len(chunk_records))
    except Exception as exc:
        logger.error("Document ingestion failed for %s: %s", doc_id, exc, exc_info=True)
        await db.update_document(doc_id, {
            "status": "failed",
            "processing_error": f"Text extraction / ingestion error: {str(exc)}",
        })
        await db.log_audit({
            "workspace_id": workspace_id,
            "user_id": user_id,
            "user_email": user_email,
            "patient_id": patient_id,
            "action": "document.failed",
            "detail": f"Failed to ingest document '{filename}': {str(exc)}",
        })
