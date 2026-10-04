import logging
from typing import Any, Dict, List, Optional
from app.core.rbac import AuthenticatedUser, get_allowed_document_types
from app.db import postgres as db

logger = logging.getLogger("rag_service.retrieval")


async def search_chunks(
    query_embedding: List[float],
    workspace_id: str,
    user: AuthenticatedUser,
    patient_id: Optional[str] = None,
    top_k: int = 8,
) -> List[Dict[str, Any]]:
    """
    Permission-safe vector retrieval service.
    
    Guarantees:
    1. Mandatory workspace isolation: chunks outside caller's workspace_id can never be returned.
    2. Patient scoping: when patient_id is specified, strictly limits retrieval to that patient.
    3. RBAC compliance: when searching workspace-wide, excludes clinical notes from viewer/records roles.
    4. Soft-delete safety: excluded chunks belonging to soft-deleted documents.
    5. Returns joined document_name and page_number directly for instant citation rendering.
    """
    if not workspace_id:
        raise ValueError("workspace_id is mandatory for retrieval and cannot be empty")

    is_patient_scoped = bool(patient_id)
    allowed_doc_types = get_allowed_document_types(user.role, is_patient_scoped=is_patient_scoped)

    # Perform vector similarity query via pure PostgreSQL / pgvector
    results = await db.search_chunks_vector(
        query_embedding=query_embedding,
        workspace_id=workspace_id,
        patient_id=patient_id,
        allowed_doc_types=allowed_doc_types,
        top_k=top_k,
    )

    return results
