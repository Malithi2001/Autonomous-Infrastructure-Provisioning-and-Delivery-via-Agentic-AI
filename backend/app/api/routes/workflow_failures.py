"""Workflow failure diagnosis endpoints."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_permission
from app.schemas.schemas import WorkflowFailureFixPRResponse, WorkflowFailureOut
from app.services.fix_pr_service import FixPRServiceError, create_fix_pr_for_failure
from app.services.workflow_failure_service import get_workflow_failure, list_workflow_failures

router = APIRouter()


@router.get("", response_model=list[WorkflowFailureOut])
@router.get("/", response_model=list[WorkflowFailureOut], include_in_schema=False)
async def list_failures(
    limit: int = 50,
    repo_full_name: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("workflow_failures:read")),
):
    """List recent GitHub Actions failure diagnoses."""
    return await list_workflow_failures(
        db,
        limit=limit,
        repo_full_name=repo_full_name,
        status=status,
    )


@router.post("/{failure_id}/create-fix-pr", response_model=WorkflowFailureFixPRResponse)
async def create_failure_fix_pr(
    failure_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("workflow_failures:write")),
):
    """Create a low-risk GitHub workflow fix pull request for a diagnosis."""
    try:
        return await create_fix_pr_for_failure(db, str(failure_id), current_user)
    except FixPRServiceError as exc:
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{failure_id}", response_model=WorkflowFailureOut)
async def get_failure(
    failure_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("workflow_failures:read")),
):
    """Fetch one GitHub Actions failure diagnosis by id."""
    record = await get_workflow_failure(db, str(failure_id))
    if not record:
        raise HTTPException(status_code=404, detail="Workflow failure diagnosis not found.")
    return record
