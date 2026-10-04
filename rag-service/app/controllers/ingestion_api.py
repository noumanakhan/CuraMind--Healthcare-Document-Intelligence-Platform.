import uuid
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from app.core.rbac import AuthenticatedUser
from app.core.security import get_current_user, require_permission
from app.db import postgres as db
from app.schemas.documents import DocumentCreate, DocumentOut
from app.services.ingestion import process_document_background

router = APIRouter(prefix="/documents", tags=["Documents & Ingestion"])


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    name: Optional[str] = Form(None),
    type: str = Form("clinical_note"),
    user: AuthenticatedUser = Depends(require_permission("documents:create")),
):
    """
    Uploads a clinical document (PDF, DOCX, image, or text) and triggers asynchronous
    OCR, full-text extraction, chunking, and embedding generation in the background.
    Returns HTTP 202 immediately.
    """
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty"
        )

    doc_id = str(uuid.uuid4())
    doc_name = name or file.filename or "uploaded_document"

    # Insert document with 'processing' status into pure PostgreSQL
    doc_record = await db.insert_document({
        "id": doc_id,
        "workspace_id": user.workspace_id,
        "patient_id": patient_id,
        "name": doc_name,
        "type": type,
        "status": "processing",
        "source": "upload",
    })

    # Schedule background ingestion worker
    background_tasks.add_task(
        process_document_background,
        doc_id=doc_id,
        workspace_id=user.workspace_id,
        patient_id=patient_id,
        file_bytes=file_bytes,
        filename=doc_name,
        user_id=user.id,
        user_email=user.email,
    )

    return DocumentOut(**doc_record)


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: DocumentCreate,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(require_permission("documents:create")),
):
    """
    Direct JSON document creation with optional text and structured fields.
    """
    doc_id = str(uuid.uuid4())
    doc_record = await db.insert_document({
        "id": doc_id,
        "workspace_id": user.workspace_id,
        "patient_id": payload.patient_id,
        "name": payload.name,
        "type": payload.type,
        "date": payload.date,
        "status": "processing" if payload.full_text else "processed",
        "source": payload.source or "manual_entry",
        "full_text": payload.full_text,
    })

    # Insert any initial structured extracted fields
    if payload.fields:
        for f in payload.fields:
            await db.insert_extracted_field({
                "document_id": doc_id,
                "workspace_id": user.workspace_id,
                "label": f.label,
                "value": f.value,
                "confidence": f.confidence or 1.0,
                "flagged": f.flagged or False,
            })

    if payload.full_text:
        background_tasks.add_task(
            process_document_background,
            doc_id=doc_id,
            workspace_id=user.workspace_id,
            patient_id=payload.patient_id,
            file_bytes=payload.full_text.encode("utf-8"),
            filename=payload.name,
            user_id=user.id,
            user_email=user.email,
        )

    return DocumentOut(**doc_record)


@router.get("", response_model=List[DocumentOut])
async def list_documents(
    patient_id: Optional[str] = None,
    user: AuthenticatedUser = Depends(require_permission("documents:view")),
):
    docs = await db.list_documents(workspace_id=user.workspace_id, patient_id=patient_id)
    return [DocumentOut(**d) for d in docs]


@router.get("/{id}", response_model=DocumentOut)
async def get_document(
    id: str,
    user: AuthenticatedUser = Depends(require_permission("documents:view")),
):
    doc = await db.get_document(id, workspace_id=user.workspace_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    fields = await db.list_extracted_fields(id, workspace_id=user.workspace_id)
    doc["extracted_fields"] = fields
    return DocumentOut(**doc)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    id: str,
    user: AuthenticatedUser = Depends(require_permission("documents:archive")),
):
    success = await db.soft_delete_document(id, workspace_id=user.workspace_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    await db.log_audit({
        "workspace_id": user.workspace_id,
        "user_id": user.id,
        "user_email": user.email,
        "action": "document.archived",
        "detail": f"Document {id} was soft-deleted and removed from vector search index.",
    })
    return None
