"""
CuraMind Authorization-Safe Retriever — LangChain BaseRetriever wrapper.

LANGCHAIN RESPONSIBILITY:
  - Implements BaseRetriever interface so the retriever is composable in
    a LangChain LCEL pipeline (retriever | prompt | llm | parser)
  - Converts raw SQL chunk dicts → LangChain Document objects with metadata

CURAMIND RESPONSIBILITY:
  - ALL authorization happens HERE before data enters LangChain:
      workspace_id  → mandatory workspace isolation
      patient_id    → patient-scoped retrieval
      user.role     → RBAC document-type filtering
  - Delegates to the existing search_chunks() SQL function which executes
    the hybrid (dense vector + sparse BM25/FTS) search with pgvector
  - The LLM NEVER receives chunks that did not pass these SQL-level filters
  - Preserves all metadata: document_id, document_name, page_number,
    chunk_index, patient_id, workspace_id — required for citation generation

Authorization flow (per do.md §8):
  Authenticated User
       ↓
  RBAC / authorization  (FastAPI middleware — NOT here)
       ↓
  workspace filter      ← enforced in SQL via workspace_id param
       ↓
  patient filter        ← enforced in SQL via patient_id param
       ↓
  vector retrieval      ← hybrid pgvector search (postgres.py)
       ↓
  authorized chunks     ← returned as LangChain Documents
       ↓
  LangChain pipeline    (prompt → llm → parser)
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict

from app.config import settings
from app.core.rbac import AuthenticatedUser
from app.services.embeddings import get_embedding_provider

logger = logging.getLogger("rag_service.retrieval")


# ---------------------------------------------------------------------------
# Thin async helper — raw SQL retrieval (authorization enforced inside)
# ---------------------------------------------------------------------------

async def search_chunks(
    query_embedding: List[float],
    workspace_id: str,
    user: AuthenticatedUser,
    patient_id: Optional[str] = None,
    top_k: int = 8,
    query_text: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Permission-safe vector & hybrid retrieval service.

    Guarantees:
    1. Mandatory workspace isolation: chunks outside caller's workspace_id can never be returned.
    2. Patient scoping: when patient_id is specified, strictly limits retrieval to that patient.
    3. RBAC compliance: when searching workspace-wide, excludes clinical notes from viewer/records roles.
    4. Soft-delete safety: excluded chunks belonging to soft-deleted documents.
    5. Hybrid ranking: combines dense vector cosine similarity with sparse keyword BM25/FTS using RRF.
    6. Returns joined document_name and page_number directly for instant citation rendering.
    """
    from app.core.rbac import get_allowed_document_types
    from app.db import postgres as db

    if not workspace_id:
        raise ValueError("workspace_id is mandatory for retrieval and cannot be empty")

    is_patient_scoped = bool(patient_id)
    allowed_doc_types = get_allowed_document_types(user.role, is_patient_scoped=is_patient_scoped)

    if query_text:
        chunks = await db.search_chunks_hybrid(
            query_text=query_text,
            query_embedding=query_embedding,
            workspace_id=workspace_id,
            patient_id=patient_id,
            allowed_doc_types=allowed_doc_types,
            top_k=top_k,
        )
    else:
        chunks = await db.search_chunks_vector(
            query_embedding=query_embedding,
            workspace_id=workspace_id,
            patient_id=patient_id,
            allowed_doc_types=allowed_doc_types,
            top_k=top_k,
        )

    if query_text is None:
        return chunks

    def _stem(word: str) -> str:
        w = word.lower()
        for suffix in ("ies", "es", "s", "ing", "ed", "tion", "tions", "ic", "al", "ment", "ments"):
            if len(w) > len(suffix) + 2 and w.endswith(suffix):
                return w[:-len(suffix)]
        return w

    stop_words = {
        "a", "an", "and", "are", "as", "at", "be", "by", "did", "do", "does",
        "for", "from", "has", "have", "how", "i", "in", "is", "it", "me", "of",
        "on", "or", "patient", "patients", "the", "this", "to", "was", "were", "what",
        "when", "where", "which", "who", "with", "during", "admission", "admitted", "discharge",
        "undergo", "underwent"
    }
    query_terms = {
        _stem(token)
        for token in re.findall(r"[a-zA-Z0-9]+", query_text or "")
        if len(token) > 2 and token.lower() not in stop_words
    }
    minimum = settings.MIN_SIMILARITY_SCORE
    relevant = []
    for chunk in chunks:
        dense_score = float(chunk.get("dense_similarity", chunk.get("similarity", 0.0)) or 0.0)
        chunk_terms = {
            _stem(token)
            for token in re.findall(r"[a-zA-Z0-9]+", chunk.get("chunk_text", ""))
        }
        if dense_score >= minimum or query_terms.intersection(chunk_terms):
            relevant.append(chunk)
    return relevant


# ---------------------------------------------------------------------------
# LangChain BaseRetriever — composable in LCEL pipelines
# ---------------------------------------------------------------------------

class CuraMindAuthorizedRetriever(BaseRetriever):
    """Authorized BaseRetriever adapter over the existing PostgreSQL/pgvector search."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    user: AuthenticatedUser
    patient_id: Optional[str] = None
    top_k: int = 8

    def get_relevant_chunks(self, query: str) -> List[Dict[str, Any]]:
        """Sync compatibility helper; use await_chunks or ainvoke in async code."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.await_chunks(query))
        raise RuntimeError("Use await_chunks() or ainvoke() from an async context")

    async def await_chunks(self, query: str) -> List[Dict[str, Any]]:
        """Return authorized raw chunks for existing callers and citation code."""
        query_embedding = get_embedding_provider().embed_text(query)
        return await search_chunks(
            query_embedding=query_embedding,
            workspace_id=self.user.workspace_id,
            user=self.user,
            patient_id=self.patient_id,
            top_k=self.top_k,
            query_text=query,
        )

    @staticmethod
    def _to_document(chunk: Dict[str, Any]) -> Document:
        metadata = {key: value for key, value in chunk.items() if key != "chunk_text"}
        return Document(page_content=chunk.get("chunk_text", ""), metadata=metadata)

    def _get_relevant_documents(self, query: str, *, run_manager: Any) -> List[Document]:
        return [self._to_document(chunk) for chunk in self.get_relevant_chunks(query)]

    async def _aget_relevant_documents(self, query: str, *, run_manager: Any) -> List[Document]:
        chunks = await self.await_chunks(query)
        return [self._to_document(chunk) for chunk in chunks]
