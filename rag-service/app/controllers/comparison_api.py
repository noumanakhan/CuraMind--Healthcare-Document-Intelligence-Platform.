from fastapi import APIRouter, Depends, HTTPException, status
from app.core.rate_limiter import compare_rate_limiter
from app.core.rbac import AuthenticatedUser
from app.core.security import require_permission
from app.schemas.comparison import DocumentCompareRequest, DocumentComparisonResponse
from app.services.comparison import compare_documents

router = APIRouter(tags=["Document Comparison"])


@router.post("/patients/{patient_id}/documents/compare", response_model=DocumentComparisonResponse)
async def compare_patient_documents(
    patient_id: str,
    payload: DocumentCompareRequest,
    user: AuthenticatedUser = Depends(require_permission("documents:compare")),
):
    """
    Compares two clinical documents scoped to a specific patient's chart.
    Enforces rate limits and deterministic structured + full-text diffing.
    """
    compare_rate_limiter.check(f"{user.workspace_id}:{user.id}")
    return await compare_documents(
        doc1_id=payload.doc1_id,
        doc2_id=payload.doc2_id,
        workspace_id=user.workspace_id,
        mode=payload.mode or "both"
    )


@router.post("/documents/compare", response_model=DocumentComparisonResponse)
async def compare_workspace_documents(
    payload: DocumentCompareRequest,
    user: AuthenticatedUser = Depends(require_permission("documents:compare")),
):
    """
    Compares two documents within the caller's workspace.
    """
    compare_rate_limiter.check(f"{user.workspace_id}:{user.id}")
    return await compare_documents(
        doc1_id=payload.doc1_id,
        doc2_id=payload.doc2_id,
        workspace_id=user.workspace_id,
        mode=payload.mode or "both"
    )
