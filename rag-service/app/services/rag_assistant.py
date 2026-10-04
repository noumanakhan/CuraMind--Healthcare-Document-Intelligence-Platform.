import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple
from app.config import settings
from app.core.rbac import AuthenticatedUser
from app.db import postgres as db
from app.schemas.conversations import CitationItem, MessageOut
from app.services.embeddings import get_embedding_provider
from app.services.llm import get_llm_provider
from app.services.retrieval import search_chunks

logger = logging.getLogger("rag_service.assistant")

CLINICAL_SYSTEM_PROMPT = """
You are the CuraMind Clinical Decision-Support AI Assistant.
Your purpose is to assist healthcare providers by retrieving and synthesizing information from the patient's verified medical records.

STRICT CLINICAL RULES:
1. Answer ONLY using the provided retrieved context chunks.
2. If the answer is not present in the retrieved records, state clearly: "No relevant clinical information was found in the patient's indexed documents."
3. NEVER formulate an autonomous medical diagnosis or prescribe treatment plans.
4. If retrieved documents contain conflicting facts or dates, highlight the discrepancy explicitly to the clinician.
5. Provide accurate source citations for all key assertions.
"""


async def ask_rag_assistant(
    conversation_id: str,
    user_query: str,
    user: AuthenticatedUser,
    patient_id: Optional[str] = None,
    top_k: int = 8,
) -> MessageOut:
    """
    Main entry point for clinical RAG assistant conversation turns.
    """
    conv = await db.get_conversation(conversation_id, workspace_id=user.workspace_id)
    if not conv:
        raise ValueError(f"Conversation {conversation_id} not found in workspace {user.workspace_id}")

    # Use conversation's patient_id if not explicitly provided
    resolved_patient_id = patient_id or conv.get("patient_id")

    # 1. Record User Message in PostgreSQL
    await db.add_message({
        "conversation_id": conversation_id,
        "role": "user",
        "content": user_query,
        "citations": [],
    })

    # 2. Embed user question
    embedding_provider = get_embedding_provider()
    query_embedding = embedding_provider.embed_text(user_query)

    # 3. Retrieve relevant chunks (permission-safe by construction)
    chunks = await search_chunks(
        query_embedding=query_embedding,
        workspace_id=user.workspace_id,
        user=user,
        patient_id=resolved_patient_id,
        top_k=top_k,
    )

    # 4. If no chunks found, return explicit clinical refusal
    if not chunks:
        refusal_content = (
            "No relevant clinical information was found in this patient's indexed documents "
            "to answer your question."
        )
        msg_record = await db.add_message({
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": refusal_content,
            "citations": [],
        })
        return MessageOut(
            id=msg_record["id"],
            conversation_id=conversation_id,
            role="assistant",
            content=refusal_content,
            citations=[],
            created_at=msg_record["created_at"],
        )

    # 5. Call LLM provider
    llm = get_llm_provider()
    answer_text = llm.generate_response(
        system_prompt=CLINICAL_SYSTEM_PROMPT,
        user_prompt=user_query,
        context_chunks=chunks,
    )

    is_refusal = (
        "no relevant clinical information" in answer_text.lower() or
        "not found in the patient" in answer_text.lower()
    )

    # 6. Extract citations only if not refused
    citations: List[CitationItem] = []
    if not is_refusal:
        seen_docs = set()
        for ch in chunks:
            doc_key = (ch["document_id"], ch.get("page_number"))
            if doc_key not in seen_docs:
                seen_docs.add(doc_key)
                citations.append(CitationItem(
                    document_id=ch["document_id"],
                    document_name=ch["document_name"],
                    page_number=ch.get("page_number"),
                    chunk_index=ch.get("chunk_index"),
                    snippet=ch["chunk_text"][:120].strip() + "..."
                ))

    # 7. Persist Assistant message with citations in PostgreSQL
    citations_data = [c.model_dump() for c in citations]
    msg_record = await db.add_message({
        "conversation_id": conversation_id,
        "role": "assistant",
        "content": answer_text,
        "citations": citations_data,
    })

    # 8. Log Audit Event
    await db.log_audit({
        "workspace_id": user.workspace_id,
        "user_id": user.id,
        "user_email": user.email,
        "patient_id": resolved_patient_id,
        "action": "rag.query",
        "detail": f"RAG query in conversation {conversation_id} with {len(citations)} citations generated.",
    })

    return MessageOut(
        id=msg_record["id"],
        conversation_id=conversation_id,
        role="assistant",
        content=answer_text,
        citations=citations,
        created_at=msg_record["created_at"],
    )
