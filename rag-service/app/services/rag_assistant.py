"""
CuraMind Clinical RAG Assistant — LangChain LCEL pipeline.

LANGCHAIN RESPONSIBILITY:
  - ChatPromptTemplate: structures system instructions + clinical safety
    rules + retrieved context + conversation history + user question
  - StrOutputParser: extracts plain text from the LLM's ChatMessage response
  - LCEL pipeline composition: prompt | llm | parser

CURAMIND RESPONSIBILITY:
  - All authorization (workspace_id / patient_id / RBAC) happens BEFORE
    any data enters LangChain — via CuraMindAuthorizedRetriever
  - Conversation persistence: PostgreSQL (conversations + messages tables)
    remains the source of truth; LangChain is NOT used for memory/state
  - Citation extraction: built from retrieved chunk metadata AFTER the LLM
    responds — citations are never invented by the LLM
  - Refusal detection: explicit no-match guard before building citations
  - Audit logging: PostgreSQL audit events recorded outside LangChain
  - Rate limiting: enforced at the API route layer, not here

RAG flow (per do.md §10):
  User question
       ↓
  CuraMindAuthorizedRetriever.await_chunks()  ← authorized, pre-filtered
       ↓
  Format context from chunk dicts
       ↓
  LangChain ChatPromptTemplate (SystemMessage + HumanMessage)
       ↓
  LangChain LLM (ChatGoogleGenerativeAI / ChatOpenAI / ChatAnthropic)
       ↓
  LangChain StrOutputParser
       ↓
  CuraMind citation extraction from chunk metadata  ← NOT from LLM output
       ↓
  PostgreSQL: persist message + citations
       ↓
  API response (MessageOut)
"""

import logging
from typing import Any, Dict, List, Optional

from app.core.rbac import AuthenticatedUser
from app.db import postgres as db
from app.schemas.conversations import CitationItem, MessageOut
from app.services.retrieval import CuraMindAuthorizedRetriever
from app.services.llm import MockLLMProvider, get_llm_provider, is_greeting_or_conversational
from app.services.workspace_intelligence import answer_workspace_query

logger = logging.getLogger("rag_service.assistant")


# ---------------------------------------------------------------------------
# LangChain prompt template — structured clinical prompt
# ---------------------------------------------------------------------------

def _build_lc_prompt_template():
    """
    Build the LangChain ChatPromptTemplate for the CuraMind clinical RAG pipeline.

    Structure (per do.md §3):
      1. System instructions (role, constraints)
      2. Clinical safety instructions (grounding, refusal, disclaimer)
      3. Retrieved context (pre-authorized chunk text + source citations)
      4. Conversation history (last N turns for multi-turn context)
      5. User question

    Returns None if langchain_core is unavailable (fallback to legacy path).
    """
    try:
        from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate

        system_template = (
            "You are the CuraMind Clinical Decision-Support AI Assistant.\n"
            "Your purpose is to assist healthcare providers by retrieving and "
            "synthesizing information from the patient's verified medical records.\n\n"
            "STRICT CLINICAL RULES:\n"
            "1. Answer clinical questions ONLY using the provided retrieved context chunks.\n"
            "2. If the answer is not present in the retrieved records, state clearly: "
            "\"No relevant clinical information was found in the patient's indexed documents.\"\n"
            "3. For polite greetings or questions about your capabilities, respond warmly "
            "and explain how you can help summarize and inspect this patient's medical chart.\n"
            "4. NEVER formulate an autonomous medical diagnosis or prescribe treatment plans.\n"
            "5. If retrieved documents contain conflicting facts or dates, highlight the "
            "discrepancy explicitly to the clinician.\n"
            "6. Provide accurate source citations for all key assertions.\n\n"
            "RETRIEVED PATIENT CONTEXT:\n"
            "{context}\n\n"
            "CONVERSATION HISTORY (most recent last):\n"
            "{history}"
        )

        human_template = "Clinician Question: {question}"

        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template(human_template),
        ])
        return prompt
    except ImportError:
        logger.warning("langchain_core not available — falling back to legacy LLM path")
        return None


# ---------------------------------------------------------------------------
# Context formatting helpers
# ---------------------------------------------------------------------------

def _format_context(chunks: List[Dict[str, Any]]) -> str:
    """Format retrieved chunks as a clearly attributed context block."""
    if not chunks:
        return "No relevant records retrieved."
    parts = []
    for ch in chunks:
        doc = ch.get("document_name", "Unknown Document")
        page = ch.get("page_number", 1)
        text = ch.get("chunk_text", "").strip()
        parts.append(f"[Source: {doc}, Page {page}]\n{text}")
    return "\n\n".join(parts)


def _format_history(messages: List[Dict[str, Any]], max_turns: int = 4) -> str:
    """
    Format the last `max_turns` conversation turns as plain text.

    PostgreSQL is the source of truth for conversation history.
    LangChain is used only to FORMAT the history into the prompt — it does
    NOT store or manage conversation state.

    max_turns is deliberately small to keep the LLM context window efficient
    and avoid sending the entire conversation history (per do.md §13).
    """
    if not messages:
        return "None"
    recent = messages[-max_turns * 2:]  # Each turn = 1 user + 1 assistant msg
    lines = []
    for m in recent:
        role = m.get("role", "user").capitalize()
        content = (m.get("content") or "").strip()[:500]  # cap per-message length
        lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "None"


# ---------------------------------------------------------------------------
# Main RAG assistant entry point
# ---------------------------------------------------------------------------

async def ask_rag_assistant(
    conversation_id: str,
    user_query: str,
    user: AuthenticatedUser,
    patient_id: Optional[str] = None,
    top_k: int = 8,
) -> MessageOut:
    """
    Main entry point for clinical RAG assistant conversation turns.

    Authorization flow:
      The CuraMindAuthorizedRetriever enforces workspace_id + patient_id +
      RBAC document-type filtering at the SQL level BEFORE chunks are passed
      to the LangChain pipeline. LangChain never performs authorization.
    """
    # ── 0. Validate conversation belongs to this workspace ──────────────────
    conv = await db.get_conversation(conversation_id, workspace_id=user.workspace_id)
    if not conv:
        raise ValueError(f"Conversation {conversation_id} not found in workspace {user.workspace_id}")

    resolved_patient_id = patient_id or conv.get("patient_id")
    # Load history before writing this turn so the current question is not duplicated.
    try:
        prior_messages = await db.list_messages(conversation_id) or []
    except Exception:
        logger.exception("Unable to load prior conversation messages; continuing without history")
        prior_messages = []
    history_text = _format_history(prior_messages)

    await db.add_message({
        "conversation_id": conversation_id,
        "role": "user",
        "content": user_query,
        "citations": [],
    })

    if is_greeting_or_conversational(user_query):
        greeting_reply = (
            "Hello! I am your **CuraMind Clinical Decision-Support Assistant**. \n\n"
            "I can help you in two ways:\n"
            "1. **App data queries** — Ask me about patients, appointments, documents in the vault, "
            "admission/discharge status, how many records there are, etc.\n"
            "2. **Document analysis** — Upload a clinical PDF and ask me to summarise it, "
            "find diagnoses, medications, lab values, follow-up actions, and more.\n\n"
            "How can I help you today?"
        )
        msg_record = await db.add_message({
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": greeting_reply,
            "citations": [],
        })
        return MessageOut(
            id=msg_record["id"], conversation_id=conversation_id, role="assistant",
            content=greeting_reply, citations=[], created_at=msg_record["created_at"],
        )

    # ── 1b. Workspace intelligence layer — app-level queries ────────────────
    # These are questions about the application's own data (patient counts,
    # appointments, document vault, etc.) — answered from backend API directly
    # without going through the RAG document retriever.
    try:
        token = getattr(user, 'raw_token', None) or getattr(user, 'token', None) or ''
        workspace_answer = await answer_workspace_query(
            query=user_query,
            token=token,
            workspace_id=user.workspace_id,
        )
        if workspace_answer:
            msg_record = await db.add_message({
                "conversation_id": conversation_id,
                "role": "assistant",
                "content": workspace_answer,
                "citations": [],
            })
            return MessageOut(
                id=msg_record["id"], conversation_id=conversation_id, role="assistant",
                content=workspace_answer, citations=[], created_at=msg_record["created_at"],
            )
    except Exception as wi_err:
        logger.warning(f"Workspace intelligence lookup failed ({wi_err}), falling through to RAG retriever.")

    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnableParallel, RunnablePassthrough

    retriever = CuraMindAuthorizedRetriever(user=user, patient_id=resolved_patient_id, top_k=top_k)
    prompt_template = _build_lc_prompt_template()
    if prompt_template is None:
        raise RuntimeError("LangChain prompt components are unavailable; refusing to use a fallback answer path")

    retrieval_stage = (
        RunnableParallel({"question": RunnablePassthrough(), "documents": retriever})
        | RunnableLambda(lambda result: {
            "question": result["question"],
            "documents": result["documents"],
            "chunks": [
                {**document.metadata, "chunk_text": document.page_content}
                for document in result["documents"]
            ],
            "context": _format_context([
                {**document.metadata, "chunk_text": document.page_content}
                for document in result["documents"]
            ]),
            "history": history_text,
        })
    )

    provider = get_llm_provider()
    refusal_text = (
        "No relevant clinical information was found in this patient's indexed documents "
        "to answer your question."
    )

    def _safe_llm_answer(payload: Dict[str, Any]) -> str:
        if isinstance(provider, MockLLMProvider):
            return provider.generate_response(
                system_prompt=CLINICAL_SYSTEM_PROMPT,
                user_prompt=payload["question"],
                context_chunks=payload["chunks"],
            )
        try:
            lc_getter = getattr(provider, "_get_lc_model", None)
            lc_model = lc_getter() if lc_getter else None
            if lc_model is not None:
                chain = prompt_template | lc_model | StrOutputParser()
                res = chain.invoke({
                    "context": payload["context"],
                    "history": payload["history"],
                    "question": payload["question"],
                })
                if res and res.strip():
                    return res
        except Exception as e:
            logger.warning(f"LangChain LLM invocation failed ({e}), falling back to provider generate_response")
        
        return provider.generate_response(
            system_prompt=CLINICAL_SYSTEM_PROMPT,
            user_prompt=payload["question"],
            context_chunks=payload["chunks"],
        )

    answer_for_retrieved_context = RunnableLambda(_safe_llm_answer)

    answer_branch = RunnableBranch(
        (lambda payload: not payload["documents"], RunnableLambda(lambda _: refusal_text)),
        answer_for_retrieved_context,
    ) | StrOutputParser()
    rag_chain = (
        retrieval_stage
        | RunnableParallel({"retrieval": RunnablePassthrough(), "answer": answer_branch})
        | RunnableLambda(lambda result: {**result["retrieval"], "answer": result["answer"]})
    )
    result = await rag_chain.ainvoke(user_query)
    answer_text = result["answer"]
    if not isinstance(answer_text, str) or not answer_text.strip():
        answer_text = refusal_text
    chunks = result["chunks"]

    is_refusal = (
        "no relevant clinical information" in answer_text.lower()
        or "not found in the patient" in answer_text.lower()
    )
    citations: List[CitationItem] = []
    if not is_refusal:
        seen_pages = set()
        for chunk in chunks:
            document_id = chunk.get("document_id")
            document_name = chunk.get("document_name")
            if not document_id or not document_name:
                continue
            page_number = chunk.get("page_number")
            page_key = (document_id, page_number)
            if page_key in seen_pages:
                continue
            seen_pages.add(page_key)
            snippet = chunk["chunk_text"][:120].strip()
            citations.append(CitationItem(
                document_id=document_id,
                document_name=document_name,
                page_number=page_number,
                chunk_index=chunk.get("chunk_index"),
                snippet=snippet + ("..." if len(chunk["chunk_text"].strip()) > 120 else ""),
            ))

    citations_data = [citation.model_dump() for citation in citations]
    msg_record = await db.add_message({
        "conversation_id": conversation_id,
        "role": "assistant",
        "content": answer_text,
        "citations": citations_data,
    })
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


# System prompt is passed to the explicit deterministic MockLLMProvider.
CLINICAL_SYSTEM_PROMPT = """
You are the CuraMind Clinical Decision-Support AI Assistant.
Your purpose is to assist healthcare providers by retrieving and synthesizing information from the patient's verified medical records.

STRICT CLINICAL RULES:
1. Answer clinical questions ONLY using the provided retrieved context chunks.
2. If the answer is not present in the retrieved records, state clearly: "No relevant clinical information was found in the patient's indexed documents."
3. For polite greetings or general inquiries about your capabilities, respond cordially and explain how you can help review this patient's records.
4. NEVER formulate an autonomous medical diagnosis or prescribe treatment plans.
5. If retrieved documents contain conflicting facts or dates, highlight the discrepancy explicitly to the clinician.
6. Provide accurate source citations for all key assertions.
"""
