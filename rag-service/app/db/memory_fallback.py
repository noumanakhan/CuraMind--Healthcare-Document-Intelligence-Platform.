import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def utcnow_str() -> str:
    return datetime.now(timezone.utc).isoformat()


def cosine_distance(vec1: List[float], vec2: List[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 1.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 1.0
    sim = dot / (norm1 * norm2)
    # Clamp cosine similarity between -1 and 1
    sim = max(-1.0, min(1.0, sim))
    return 1.0 - sim


class InMemoryPostgresStore:
    """
    In-memory PostgreSQL store for RAG service.
    Implements identical relational semantics and pgvector cosine distance similarity search
    allowing seamless unit testing and zero-dependency standalone execution.
    """
    def __init__(self):
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.extracted_fields: Dict[str, Dict[str, Any]] = {}
        self.document_chunks: Dict[str, Dict[str, Any]] = {}
        self.conversations: Dict[str, Dict[str, Any]] = {}
        self.conversation_messages: Dict[str, Dict[str, Any]] = {}
        self.audit_events: Dict[str, Dict[str, Any]] = {}

    def reset(self):
        self.documents.clear()
        self.extracted_fields.clear()
        self.document_chunks.clear()
        self.conversations.clear()
        self.conversation_messages.clear()
        self.audit_events.clear()

    # --- Documents ---
    async def insert_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        doc_id = doc.get("id") or str(uuid.uuid4())
        record = {
            "id": doc_id,
            "workspace_id": doc["workspace_id"],
            "patient_id": doc["patient_id"],
            "name": doc["name"],
            "type": doc["type"],
            "date": doc.get("date", datetime.now(timezone.utc).strftime("%d %b %Y")),
            "status": doc.get("status", "processing"),
            "processing_error": doc.get("processing_error"),
            "full_text": doc.get("full_text"),
            "source": doc.get("source"),
            "is_deleted": doc.get("is_deleted", False),
            "created_at": doc.get("created_at") or utcnow_str(),
            "updated_at": doc.get("updated_at") or utcnow_str(),
        }
        self.documents[doc_id] = record
        return record

    async def get_document(self, doc_id: str, workspace_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        doc = self.documents.get(doc_id)
        if not doc or doc.get("is_deleted", False):
            return None
        if workspace_id and doc["workspace_id"] != workspace_id:
            return None
        return dict(doc)

    async def update_document(self, doc_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        doc = self.documents.get(doc_id)
        if not doc:
            return None
        doc.update(updates)
        doc["updated_at"] = utcnow_str()
        return dict(doc)

    async def list_documents(self, workspace_id: str, patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for doc in self.documents.values():
            if doc.get("is_deleted", False):
                continue
            if doc["workspace_id"] != workspace_id:
                continue
            if patient_id and doc["patient_id"] != patient_id:
                continue
            results.append(dict(doc))
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return results

    async def soft_delete_document(self, doc_id: str, workspace_id: str) -> bool:
        doc = self.documents.get(doc_id)
        if not doc or doc["workspace_id"] != workspace_id:
            return False
        doc["is_deleted"] = True
        doc["updated_at"] = utcnow_str()
        return True

    # --- Extracted Fields ---
    async def insert_extracted_field(self, field: Dict[str, Any]) -> Dict[str, Any]:
        f_id = field.get("id") or str(uuid.uuid4())
        record = {
            "id": f_id,
            "document_id": field["document_id"],
            "workspace_id": field["workspace_id"],
            "label": field["label"],
            "value": field["value"],
            "confidence": float(field.get("confidence", 1.0)),
            "flagged": bool(field.get("flagged", False)),
            "confirmed": bool(field.get("confirmed", False)),
            "created_at": field.get("created_at") or utcnow_str(),
        }
        self.extracted_fields[f_id] = record
        return record

    async def list_extracted_fields(self, document_id: str, workspace_id: str) -> List[Dict[str, Any]]:
        return [
            dict(f) for f in self.extracted_fields.values()
            if f["document_id"] == document_id and f["workspace_id"] == workspace_id
        ]

    # --- Document Chunks & Vector Similarity Search ---
    async def insert_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        created = []
        for ch in chunks:
            ch_id = ch.get("id") or str(uuid.uuid4())
            record = {
                "id": ch_id,
                "document_id": ch["document_id"],
                "workspace_id": ch["workspace_id"],
                "patient_id": ch["patient_id"],
                "chunk_text": ch["chunk_text"],
                "page_number": ch.get("page_number"),
                "chunk_index": ch["chunk_index"],
                "embedding": ch["embedding"],
                "created_at": ch.get("created_at") or utcnow_str(),
            }
            self.document_chunks[ch_id] = record
            created.append(record)
        return created

    async def search_chunks_vector(
        self,
        query_embedding: List[float],
        workspace_id: str,
        patient_id: Optional[str] = None,
        allowed_doc_types: Optional[List[str]] = None,
        top_k: int = 8,
    ) -> List[Dict[str, Any]]:
        candidates = []
        for ch in self.document_chunks.values():
            # 1. Strict Workspace Isolation
            if ch["workspace_id"] != workspace_id:
                continue
            # 2. Strict Patient Scoping (if provided)
            if patient_id and ch["patient_id"] != patient_id:
                continue

            # Check if parent document is deleted
            parent_doc = self.documents.get(ch["document_id"])
            if not parent_doc or parent_doc.get("is_deleted", False):
                continue

            # 3. RBAC Document Type Check (e.g. viewer cannot see clinical notes in workspace-wide queries)
            if allowed_doc_types is not None and parent_doc["type"] not in allowed_doc_types:
                continue

            dist = cosine_distance(query_embedding, ch["embedding"])
            similarity = 1.0 - dist

            candidates.append({
                "id": ch["id"],
                "document_id": ch["document_id"],
                "document_name": parent_doc["name"],
                "document_type": parent_doc["type"],
                "workspace_id": ch["workspace_id"],
                "patient_id": ch["patient_id"],
                "chunk_text": ch["chunk_text"],
                "page_number": ch.get("page_number"),
                "chunk_index": ch["chunk_index"],
                "source": parent_doc.get("source"),
                "document_date": parent_doc.get("date"),
                "document_created_at": parent_doc.get("created_at"),
                "document_updated_at": parent_doc.get("updated_at"),
                "chunk_created_at": ch.get("created_at"),
                "similarity": similarity,
                "distance": dist,
            })

        # Sort by highest similarity (lowest distance)
        candidates.sort(key=lambda x: x["similarity"], reverse=True)
        return candidates[:top_k]

    async def search_chunks_hybrid(
        self,
        query_text: str,
        query_embedding: List[float],
        workspace_id: str,
        patient_id: Optional[str] = None,
        allowed_doc_types: Optional[List[str]] = None,
        top_k: int = 8,
        rrf_k: int = 60,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining Dense Semantic Search (Vector Embeddings) and
        Sparse Keyword Search (BM25 / Exact Term Frequency) using Reciprocal Rank Fusion (RRF).
        """
        dense_results = await self.search_chunks_vector(
            query_embedding=query_embedding,
            workspace_id=workspace_id,
            patient_id=patient_id,
            allowed_doc_types=allowed_doc_types,
            top_k=len(self.document_chunks),  # full pool for ranking
        )

        if not dense_results:
            return []

        # 1. Compute Sparse Keyword Scores (exact keywords, medical acronyms, codes)
        import re
        q_tokens = [w.lower() for w in re.findall(r'[\w\.-]+', query_text) if len(w) > 1]
        
        sparse_scored = []
        for item in dense_results:
            text_lower = item["chunk_text"].lower()
            text_words = set(re.findall(r'[\w\.-]+', text_lower))
            
            # Count exact matches
            matches = sum(1 for tok in q_tokens if tok in text_words or tok in text_lower)
            # Exact phrase match bonus
            phrase_bonus = 2.0 if query_text.lower().strip() in text_lower else 0.0
            sparse_score = matches + phrase_bonus
            sparse_scored.append((item, sparse_score))

        # Rank by sparse score
        sparse_ranked = sorted(sparse_scored, key=lambda x: x[1], reverse=True)

        # 2. Reciprocal Rank Fusion (RRF)
        dense_ranks = {item["id"]: rank for rank, item in enumerate(dense_results, start=1)}
        sparse_ranks = {item["id"]: rank for rank, (item, _) in enumerate(sparse_ranked, start=1)}

        hybrid_results = []
        for item, sparse_score in sparse_scored:
            d_rank = dense_ranks.get(item["id"], len(dense_results) + 1)
            s_rank = sparse_ranks.get(item["id"], len(sparse_ranked) + 1)
            
            rrf_score = (1.0 / (rrf_k + d_rank)) + (1.0 / (rrf_k + s_rank))
            
            res_item = dict(item)
            res_item["dense_similarity"] = item["similarity"]
            res_item["sparse_score"] = sparse_score
            res_item["hybrid_score"] = round(rrf_score, 6)
            res_item["search_type"] = "hybrid (dense + keyword)"
            hybrid_results.append((res_item, rrf_score))

        # Sort by highest RRF score
        hybrid_results.sort(key=lambda x: x[1], reverse=True)
        return [item for item, _ in hybrid_results[:top_k]]

    # --- Conversations & Messages ---
    async def create_conversation(self, conv: Dict[str, Any]) -> Dict[str, Any]:
        c_id = conv.get("id") or str(uuid.uuid4())
        record = {
            "id": c_id,
            "workspace_id": conv["workspace_id"],
            "patient_id": conv.get("patient_id"),
            "user_id": conv["user_id"],
            "title": conv.get("title", "Clinical Assistant Session"),
            "created_at": conv.get("created_at") or utcnow_str(),
            "updated_at": conv.get("updated_at") or utcnow_str(),
        }
        self.conversations[c_id] = record
        return record

    async def get_conversation(self, conv_id: str, workspace_id: str) -> Optional[Dict[str, Any]]:
        conv = self.conversations.get(conv_id)
        if not conv or conv["workspace_id"] != workspace_id:
            return None
        return dict(conv)

    async def list_conversations(self, workspace_id: str, patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for conv in self.conversations.values():
            if conv["workspace_id"] != workspace_id:
                continue
            if patient_id and conv.get("patient_id") != patient_id:
                continue
            results.append(dict(conv))
        results.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return results

    async def delete_conversation(self, conv_id: str, workspace_id: str) -> bool:
        """Hard-delete conversation + cascade-delete its messages."""
        conv = self.conversations.get(conv_id)
        if not conv or conv["workspace_id"] != workspace_id:
            return False
        del self.conversations[conv_id]
        # Cascade: remove all messages belonging to this conversation
        to_remove = [mid for mid, m in self.conversation_messages.items() if m["conversation_id"] == conv_id]
        for mid in to_remove:
            del self.conversation_messages[mid]
        return True

    async def update_conversation_title(self, conv_id: str, workspace_id: str, title: str) -> bool:
        conv = self.conversations.get(conv_id)
        if not conv or conv["workspace_id"] != workspace_id:
            return False
        conv["title"] = title
        conv["updated_at"] = utcnow_str()
        return True

    async def add_message(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        m_id = msg.get("id") or str(uuid.uuid4())
        record = {
            "id": m_id,
            "conversation_id": msg["conversation_id"],
            "role": msg["role"],
            "content": msg["content"],
            "citations": msg.get("citations", []),
            "created_at": msg.get("created_at") or utcnow_str(),
        }
        self.conversation_messages[m_id] = record
        if msg["conversation_id"] in self.conversations:
            self.conversations[msg["conversation_id"]]["updated_at"] = record["created_at"]
        return record

    async def list_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        msgs = [
            dict(m) for m in self.conversation_messages.values()
            if m["conversation_id"] == conversation_id
        ]
        msgs.sort(key=lambda x: x.get("created_at", ""))
        return msgs

    # --- Audit Events ---
    async def log_audit(self, event: Dict[str, Any]) -> Dict[str, Any]:
        a_id = event.get("id") or str(uuid.uuid4())
        record = {
            "id": a_id,
            "workspace_id": event["workspace_id"],
            "user_id": event["user_id"],
            "user_email": event.get("user_email"),
            "patient_id": event.get("patient_id"),
            "action": event["action"],
            "detail": event.get("detail"),
            "created_at": event.get("created_at") or utcnow_str(),
        }
        self.audit_events[a_id] = record
        return record


# Global singleton instance
in_memory_store = InMemoryPostgresStore()
