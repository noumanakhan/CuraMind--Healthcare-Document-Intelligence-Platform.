from fastapi import APIRouter, Depends
from app.core.rbac import AuthenticatedUser
from app.core.security import require_permission
from app.schemas.retrieval import RetrievedChunkOut, SearchQueryRequest, SearchResponseOut
from app.services.embeddings import get_embedding_provider
from app.services.retrieval import search_chunks

router = APIRouter(prefix="/retrieval", tags=["Vector Retrieval"])


@router.post("/search", response_model=SearchResponseOut)
async def search_document_chunks(
    payload: SearchQueryRequest,
    user: AuthenticatedUser = Depends(require_permission("documents:view")),
):
    """
    Permission-safe vector retrieval endpoint.
    Guarantees strict workspace isolation, optional patient scoping, and RBAC-scoped document type filtering.
    """
    embedding_provider = get_embedding_provider()
    query_vector = embedding_provider.embed_text(payload.query)

    chunks = await search_chunks(
        query_embedding=query_vector,
        workspace_id=user.workspace_id,
        user=user,
        patient_id=payload.patient_id,
        top_k=payload.top_k or 8,
        query_text=payload.query,
    )

    chunk_models = [RetrievedChunkOut(**c) for c in chunks]
    return SearchResponseOut(
        query=payload.query,
        workspace_id=user.workspace_id,
        patient_id=payload.patient_id,
        total_results=len(chunk_models),
        chunks=chunk_models,
    )
