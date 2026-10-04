import json
import logging
from typing import Any, Dict, List, Optional
import asyncpg
from app.config import settings
from app.db.memory_fallback import in_memory_store

logger = logging.getLogger("rag_service.db")

_pool: Optional[asyncpg.Pool] = None
_using_postgres: bool = False


async def get_db_pool() -> Optional[asyncpg.Pool]:
    global _pool, _using_postgres
    if _pool is not None:
        return _pool

    dsn = settings.get_postgres_dsn
    try:
        _pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=10, timeout=3.0)
        _using_postgres = True
        logger.info(f"Connected to PostgreSQL at {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")
        return _pool
    except Exception as e:
        logger.warning(f"PostgreSQL connection failed ({e}). Falling back to in-memory PostgreSQL store.")
        _using_postgres = False
        return None


async def is_postgres_active() -> bool:
    global _using_postgres
    if _pool is None:
        await get_db_pool()
    return _using_postgres


async def init_db():
    pool = await get_db_pool()
    if pool:
        try:
            with open("app/db/schema.sql", "r") as f:
                schema_sql = f.read()
            async with pool.acquire() as conn:
                await conn.execute(schema_sql)
            logger.info("PostgreSQL schema successfully initialized.")
        except Exception as e:
            logger.error(f"Failed to execute schema.sql on PostgreSQL: {e}")


# --- Pure PostgreSQL Operations with In-Memory Adapter ---

async def insert_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not await is_postgres_active():
        return await in_memory_store.insert_document(doc)

    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO documents (id, workspace_id, patient_id, name, type, date, status, processing_error, full_text, source, is_deleted)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING id, workspace_id, patient_id, name, type, date, status, processing_error, full_text, source, is_deleted, created_at, updated_at
            """,
            doc.get("id"), doc["workspace_id"], doc["patient_id"], doc["name"], doc["type"],
            doc.get("date"), doc.get("status", "processing"), doc.get("processing_error"),
            doc.get("full_text"), doc.get("source"), doc.get("is_deleted", False)
        )
        return dict(row)


async def get_document(doc_id: str, workspace_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not await is_postgres_active():
        return await in_memory_store.get_document(doc_id, workspace_id)

    async with _pool.acquire() as conn:
        if workspace_id:
            row = await conn.fetchrow(
                "SELECT * FROM documents WHERE id = $1 AND workspace_id = $2 AND is_deleted = FALSE",
                doc_id, workspace_id
            )
        else:
            row = await conn.fetchrow(
                "SELECT * FROM documents WHERE id = $1 AND is_deleted = FALSE",
                doc_id
            )
        return dict(row) if row else None


async def update_document(doc_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not await is_postgres_active():
        return await in_memory_store.update_document(doc_id, updates)

    set_clauses = []
    values = [doc_id]
    for idx, (k, v) in enumerate(updates.items(), start=2):
        set_clauses.append(f"{k} = ${idx}")
        values.append(v)
    set_clauses.append("updated_at = CURRENT_TIMESTAMP")

    query = f"UPDATE documents SET {', '.join(set_clauses)} WHERE id = $1 RETURNING *"
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(query, *values)
        return dict(row) if row else None


async def list_documents(workspace_id: str, patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if not await is_postgres_active():
        return await in_memory_store.list_documents(workspace_id, patient_id)

    async with _pool.acquire() as conn:
        if patient_id:
            rows = await conn.fetch(
                "SELECT * FROM documents WHERE workspace_id = $1 AND patient_id = $2 AND is_deleted = FALSE ORDER BY created_at DESC",
                workspace_id, patient_id
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM documents WHERE workspace_id = $1 AND is_deleted = FALSE ORDER BY created_at DESC",
                workspace_id
            )
        return [dict(r) for r in rows]


async def soft_delete_document(doc_id: str, workspace_id: str) -> bool:
    if not await is_postgres_active():
        return await in_memory_store.soft_delete_document(doc_id, workspace_id)

    async with _pool.acquire() as conn:
        res = await conn.execute(
            "UPDATE documents SET is_deleted = TRUE, updated_at = CURRENT_TIMESTAMP WHERE id = $1 AND workspace_id = $2",
            doc_id, workspace_id
        )
        return res != "UPDATE 0"


# --- Extracted Fields ---

async def insert_extracted_field(field: Dict[str, Any]) -> Dict[str, Any]:
    if not await is_postgres_active():
        return await in_memory_store.insert_extracted_field(field)

    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO extracted_fields (id, document_id, workspace_id, label, value, confidence, flagged, confirmed)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
            """,
            field.get("id"), field["document_id"], field["workspace_id"], field["label"],
            field["value"], field.get("confidence", 1.0), field.get("flagged", False), field.get("confirmed", False)
        )
        return dict(row)


async def list_extracted_fields(document_id: str, workspace_id: str) -> List[Dict[str, Any]]:
    if not await is_postgres_active():
        return await in_memory_store.list_extracted_fields(document_id, workspace_id)

    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM extracted_fields WHERE document_id = $1 AND workspace_id = $2 ORDER BY created_at ASC",
            document_id, workspace_id
        )
        return [dict(r) for r in rows]


# --- Chunks & pgvector Similarity Search ---

async def insert_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not await is_postgres_active():
        return await in_memory_store.insert_chunks(chunks)

    results = []
    async with _pool.acquire() as conn:
        async with conn.transaction():
            for ch in chunks:
                emb_str = f"[{','.join(map(str, ch['embedding']))}]"
                row = await conn.fetchrow(
                    """
                    INSERT INTO document_chunks (id, document_id, workspace_id, patient_id, chunk_text, page_number, chunk_index, embedding)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8::vector)
                    RETURNING id, document_id, workspace_id, patient_id, chunk_text, page_number, chunk_index, created_at
                    """,
                    ch.get("id"), ch["document_id"], ch["workspace_id"], ch["patient_id"],
                    ch["chunk_text"], ch.get("page_number"), ch["chunk_index"], emb_str
                )
                results.append(dict(row))
    return results


async def search_chunks_vector(
    query_embedding: List[float],
    workspace_id: str,
    patient_id: Optional[str] = None,
    allowed_doc_types: Optional[List[str]] = None,
    top_k: int = 8,
) -> List[Dict[str, Any]]:
    if not await is_postgres_active():
        return await in_memory_store.search_chunks_vector(
            query_embedding, workspace_id, patient_id, allowed_doc_types, top_k
        )

    emb_str = f"[{','.join(map(str, query_embedding))}]"
    params: List[Any] = [workspace_id, emb_str]
    where_clauses = ["c.workspace_id = $1", "d.is_deleted = FALSE"]

    if patient_id:
        params.append(patient_id)
        where_clauses.append(f"c.patient_id = ${len(params)}")

    if allowed_doc_types is not None:
        params.append(allowed_doc_types)
        where_clauses.append(f"d.type = ANY(${len(params)})")

    params.append(top_k)
    limit_clause = f"${len(params)}"

    sql = f"""
    SELECT 
        c.id,
        c.document_id,
        d.name AS document_name,
        d.type AS document_type,
        c.workspace_id,
        c.patient_id,
        c.chunk_text,
        c.page_number,
        c.chunk_index,
        1 - (c.embedding <=> $2::vector) AS similarity,
        (c.embedding <=> $2::vector) AS distance
    FROM document_chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE {' AND '.join(where_clauses)}
    ORDER BY c.embedding <=> $2::vector ASC
    LIMIT {limit_clause}
    """

    async with _pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
        return [dict(r) for r in rows]


# --- Conversations & Messages ---

async def create_conversation(conv: Dict[str, Any]) -> Dict[str, Any]:
    if not await is_postgres_active():
        return await in_memory_store.create_conversation(conv)

    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO conversations (id, workspace_id, patient_id, user_id, title)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            conv.get("id"), conv["workspace_id"], conv.get("patient_id"), conv["user_id"], conv.get("title", "Clinical Assistant Session")
        )
        return dict(row)


async def get_conversation(conv_id: str, workspace_id: str) -> Optional[Dict[str, Any]]:
    if not await is_postgres_active():
        return await in_memory_store.get_conversation(conv_id, workspace_id)

    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM conversations WHERE id = $1 AND workspace_id = $2",
            conv_id, workspace_id
        )
        return dict(row) if row else None


async def list_conversations(workspace_id: str, patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if not await is_postgres_active():
        return await in_memory_store.list_conversations(workspace_id, patient_id)

    async with _pool.acquire() as conn:
        if patient_id:
            rows = await conn.fetch(
                "SELECT * FROM conversations WHERE workspace_id = $1 AND patient_id = $2 ORDER BY updated_at DESC",
                workspace_id, patient_id
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM conversations WHERE workspace_id = $1 ORDER BY updated_at DESC",
                workspace_id
            )
        return [dict(r) for r in rows]


async def add_message(msg: Dict[str, Any]) -> Dict[str, Any]:
    if not await is_postgres_active():
        return await in_memory_store.add_message(msg)

    citations_json = json.dumps(msg.get("citations", []))
    async with _pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                INSERT INTO conversation_messages (id, conversation_id, role, content, citations)
                VALUES ($1, $2, $3, $4, $5::jsonb)
                RETURNING *
                """,
                msg.get("id"), msg["conversation_id"], msg["role"], msg["content"], citations_json
            )
            await conn.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = $1",
                msg["conversation_id"]
            )
            res = dict(row)
            if isinstance(res.get("citations"), str):
                res["citations"] = json.loads(res["citations"])
            return res


async def list_messages(conversation_id: str) -> List[Dict[str, Any]]:
    if not await is_postgres_active():
        return await in_memory_store.list_messages(conversation_id)

    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM conversation_messages WHERE conversation_id = $1 ORDER BY created_at ASC",
            conversation_id
        )
        results = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("citations"), str):
                d["citations"] = json.loads(d["citations"])
            results.append(d)
        return results


# --- Audit Logging ---

async def log_audit(event: Dict[str, Any]) -> Dict[str, Any]:
    if not await is_postgres_active():
        return await in_memory_store.log_audit(event)

    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO audit_events (id, workspace_id, user_id, user_email, patient_id, action, detail)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
            """,
            event.get("id"), event["workspace_id"], event["user_id"], event.get("user_email"),
            event.get("patient_id"), event["action"], event.get("detail")
        )
        return dict(row)
