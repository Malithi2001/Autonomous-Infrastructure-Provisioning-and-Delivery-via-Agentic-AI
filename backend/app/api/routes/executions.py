"""Execution history endpoints."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_permission
from app.models.models import Execution
from app.schemas.schemas import ExecutionOut

router = APIRouter()


@router.get("/", response_model=list[ExecutionOut])
async def list_executions(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("executions:read")),
):
    """List recent agent executions with full audit trail (newest first)."""
    stmt = (
        select(Execution)
        .order_by(Execution.started_at.desc())
        .limit(min(limit, 200))
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{execution_id}", response_model=ExecutionOut)
async def get_execution(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("executions:read")),
):
    """Get details of a specific execution including AI reasoning steps."""
    record = await db.get(Execution, str(execution_id))
    if not record:
        raise HTTPException(status_code=404, detail="Execution not found.")
    return record