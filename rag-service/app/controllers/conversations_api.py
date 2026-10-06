import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.rate_limiter import rag_rate_limiter
from app.core.rbac import AuthenticatedUser
from app.core.security import require_permission
from app.db import postgres as db
from app.schemas.conversations import (
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    MessageCreate,
    MessageOut,
)
from app.services.rag_assistant import ask_rag_assistant

router = APIRouter(tags=["Conversations & RAG Assistant"])
logger = logging.getLogger("rag_service.conversations")


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
    title = payload.title if payload and payload.title else "New Chat"
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
    payload: Optional[ConversationCreate] = None,
    user: AuthenticatedUser = Depends(require_permission("rag:chat")),
):
    title = payload.title if payload and payload.title else "New Chat"
    pid = payload.patient_id if payload else None
    conv = await db.create_conversation({
        "workspace_id": user.workspace_id,
        "patient_id": pid,
        "user_id": user.id,
        "title": title,
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

        # Auto-update conversation title if it currently has a generic name
        conv = await db.get_conversation(conversation_id, workspace_id=user.workspace_id)
        if conv and conv.get("title") in ("New Chat", "Clinical Assistant Session", "Chart Review"):
            clean_title = payload.content.strip().split("\n")[0][:45]
            if clean_title:
                await db.update_conversation_title(conversation_id, user.workspace_id, clean_title)

        return reply
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        logger.exception("RAG request failed for conversation %s", conversation_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The RAG provider is currently unavailable. No generated answer was returned.",
        ) from e


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut)
async def update_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    user: AuthenticatedUser = Depends(require_permission("rag:chat")),
):
    """
    Renames a conversation title with tenant isolation.
    """
    success = await db.update_conversation_title(
        conversation_id=conversation_id,
        workspace_id=user.workspace_id,
        title=payload.title,
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    conv = await db.get_conversation(conversation_id, workspace_id=user.workspace_id)
    return ConversationOut(**conv)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    user: AuthenticatedUser = Depends(require_permission("rag:chat")),
):
    """
    Hard-deletes a conversation and all its messages from the database.
    The ON DELETE CASCADE constraint ensures all conversation_messages rows
    are automatically removed.
    """
    success = await db.delete_conversation(conversation_id, workspace_id=user.workspace_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found in the current workspace",
        )
    await db.log_audit({
        "workspace_id": user.workspace_id,
        "user_id": user.id,
        "user_email": user.email,
        "action": "conversation.deleted",
        "detail": f"Conversation {conversation_id} and all messages permanently deleted.",
    })
    return None
