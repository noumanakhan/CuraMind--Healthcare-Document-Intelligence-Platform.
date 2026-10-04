from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.rate_limiter import rag_rate_limiter
from app.core.rbac import AuthenticatedUser
from app.core.security import require_permission
from app.db import postgres as db
from app.schemas.conversations import (
    ConversationCreate,
    ConversationOut,
    MessageCreate,
    MessageOut,
)
from app.services.rag_assistant import ask_rag_assistant

router = APIRouter(tags=["Conversations & RAG Assistant"])


# --- Patient Scoped Conversations ---

@router.get("/patients/{patient_id}/conversations", response_model=List[ConversationOut])
async def list_patient_conversations(
    patient_id: str,
    user: AuthenticatedUser = Depends(require_permission("rag:chat")),
):
    convs = await db.list_conversations(workspace_id=user.workspace_id, patient_id=patient_id)
    return [ConversationOut(**c) for c in convs]


@router.post("/patients/{patient_id}/conversations", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
async def create_patient_conversation(
    patient_id: str,
    payload: Optional[ConversationCreate] = None,
    user: AuthenticatedUser = Depends(require_permission("rag:chat")),
):
    title = payload.title if payload and payload.title else "Clinical Assistant Session"
    conv = await db.create_conversation({
        "workspace_id": user.workspace_id,
        "patient_id": patient_id,
        "user_id": user.id,
        "title": title,
    })
    return ConversationOut(**conv)


# --- Workspace Scoped Conversations ---

@router.get("/conversations", response_model=List[ConversationOut])
async def list_all_conversations(
    user: AuthenticatedUser = Depends(require_permission("rag:chat")),
):
    convs = await db.list_conversations(workspace_id=user.workspace_id)
    return [ConversationOut(**c) for c in convs]


@router.post("/conversations", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
async def create_general_conversation(
    payload: ConversationCreate,
    user: AuthenticatedUser = Depends(require_permission("rag:chat")),
):
    conv = await db.create_conversation({
        "workspace_id": user.workspace_id,
        "patient_id": payload.patient_id,
        "user_id": user.id,
        "title": payload.title or "Clinical Assistant Session",
    })
    return ConversationOut(**conv)


# --- Messages & RAG Query Execution ---

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageOut])
async def get_conversation_messages(
    conversation_id: str,
    user: AuthenticatedUser = Depends(require_permission("rag:chat")),
):
    conv = await db.get_conversation(conversation_id, workspace_id=user.workspace_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    messages = await db.list_messages(conversation_id)
    return [MessageOut(**m) for m in messages]


@router.post("/conversations/{conversation_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def send_message_and_generate_rag_reply(
    conversation_id: str,
    payload: MessageCreate,
    user: AuthenticatedUser = Depends(require_permission("rag:chat")),
):
    """
    Submits a user inquiry to the RAG assistant and generates a grounded response with real citations.
    Rate limited per user/workspace.
    """
    rag_rate_limiter.check(f"{user.workspace_id}:{user.id}")

    try:
        reply = await ask_rag_assistant(
            conversation_id=conversation_id,
            user_query=payload.content,
            user=user,
        )
        return reply
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
