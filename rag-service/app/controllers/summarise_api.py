"""
summarise_api.py
────────────────
FastAPI endpoints for the full ad-hoc RAG pipeline on uploaded documents.

  POST /documents/summarise         — Upload 1 doc → hybrid retrieve → LLM summary
  POST /documents/upload-compare    — Upload 2 docs → hybrid retrieve both → LLM comparison
  POST /documents/ask               — Upload 1 doc + question → hybrid retrieve → LLM answer

All are read-only: documents are processed in-memory and NOT stored in the DB.
Permission required: documents:view
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from app.core.rate_limiter import compare_rate_limiter
from app.core.rbac import AuthenticatedUser
from app.core.security import require_permission
from app.services.summarize_and_compare import (
    summarise_document,
    compare_uploaded_documents,
    answer_question_about_document,
)

router = APIRouter(tags=["Summarise & AI Compare"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".png", ".jpg", ".jpeg", ".tiff"}
MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB


def _validate(file: UploadFile, file_bytes: bytes) -> None:
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{file.filename}' is empty."
        )
    if len(file_bytes) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File '{file.filename}' exceeds the 20 MB limit."
        )


@router.post("/documents/summarise")
async def summarise_uploaded_document(
    file: UploadFile = File(..., description="PDF, DOCX, image, or plain text to summarise"),
    user: AuthenticatedUser = Depends(require_permission("documents:view")),
):
    """
    Full RAG pipeline for a single uploaded document:
      Extract → Chunk (RecursiveCharacterTextSplitter)
              → Embed all chunks (Gemini / OpenAI / mock)
              → In-memory semantic + BM25 hybrid search
              → RRF reranking → Top-10 relevant chunks
              → LLM structured clinical summary

    Document is NOT persisted to the database.
    """
    compare_rate_limiter.check(f"{user.workspace_id}:{user.id}")
    file_bytes = await file.read()
    _validate(file, file_bytes)

    result = summarise_document(
        file_bytes=file_bytes,
        filename=file.filename or "document",
    )
    return result


@router.post("/documents/upload-compare")
async def upload_compare_documents(
    file_a: UploadFile = File(..., description="Document A"),
    file_b: UploadFile = File(..., description="Document B"),
    user: AuthenticatedUser = Depends(require_permission("documents:view")),
):
    """
    Full RAG pipeline for two uploaded documents:
      Each doc: Extract → Chunk → Embed → Hybrid retrieve (semantic + BM25 + RRF)
      Both sets of top-K passages → LLM structured field-by-field comparison.

    Documents are NOT persisted.
    """
    compare_rate_limiter.check(f"{user.workspace_id}:{user.id}")
    bytes_a = await file_a.read()
    bytes_b = await file_b.read()
    _validate(file_a, bytes_a)
    _validate(file_b, bytes_b)

    result = compare_uploaded_documents(
        file_a_bytes=bytes_a,
        filename_a=file_a.filename or "document_a",
        file_b_bytes=bytes_b,
        filename_b=file_b.filename or "document_b",
    )
    return result


@router.post("/documents/ask")
async def ask_about_uploaded_document(
    file: UploadFile = File(..., description="Document to query"),
    question: str = Form(..., description="Clinician question about the document"),
    user: AuthenticatedUser = Depends(require_permission("documents:view")),
):
    """
    Full RAG Q&A pipeline for a single uploaded document:
      Extract → Chunk → Embed → Hybrid retrieve (semantic + BM25 + RRF)
      → Top-6 most relevant chunks → LLM answer with page citations.

    Use this endpoint when the clinician uploads a doc and asks specific questions
    via the Clinical Assistant. Document is NOT persisted.
    """
    compare_rate_limiter.check(f"{user.workspace_id}:{user.id}")

    if not question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty."
        )

    file_bytes = await file.read()
    _validate(file, file_bytes)

    result = answer_question_about_document(
        question=question,
        file_bytes=file_bytes,
        filename=file.filename or "document",
    )
    return result
