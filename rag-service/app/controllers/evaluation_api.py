from fastapi import APIRouter, Depends
from app.core.rbac import AuthenticatedUser
from app.core.security import require_permission
from app.schemas.evaluation import EvaluationSummaryOut
from app.services.evaluation import run_evaluation_benchmark

router = APIRouter(prefix="/evaluation", tags=["Evaluation & Benchmark"])


@router.post("/run", response_model=EvaluationSummaryOut)
async def trigger_evaluation_benchmark(
    user: AuthenticatedUser = Depends(require_permission("settings:manage")),
):
    """
    Executes the clinical Q&A benchmark suite (16 test cases) and returns groundedness,
    citation accuracy, and refusal metrics.
    Requires workspace admin permissions.
    """
    return await run_evaluation_benchmark(workspace_id=user.workspace_id, user=user)
