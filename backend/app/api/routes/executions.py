"""Execution history endpoints."""
from uuid import UUID
from fastapi import APIRouter, Depends
from app.core.security import require_permission
from app.schemas.schemas import ExecutionOut

router = APIRouter()


@router.get("/", response_model=list[ExecutionOut])
async def list_executions(
    limit: int = 50,
    current_user: dict = Depends(require_permission("executions:read")),
):
    """List recent agent executions with full audit trail."""
    # TODO: Query Execution table from DB
    return []


@router.get("/{execution_id}", response_model=ExecutionOut)
async def get_execution(
    execution_id: UUID,
    current_user: dict = Depends(require_permission("executions:read")),
):
    """Get details of a specific execution including AI reasoning steps."""
    # TODO: Fetch from DB
    raise NotImplementedError("DB query not yet wired.")
