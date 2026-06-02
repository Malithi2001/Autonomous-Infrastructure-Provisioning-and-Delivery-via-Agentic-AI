"""Evaluation evidence endpoints for final-year project demos."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_permission
from app.models.models import ApprovalRequest, Execution, WorkflowFailure

router = APIRouter()

METRICS_PATH = Path(__file__).resolve().parents[2] / "ml" / "reports" / "metrics.json"


def _load_model_metrics() -> dict[str, Any]:
    """Load generated model metrics, returning nullable fields if missing."""
    empty_metrics = {
        "dataset_size": None,
        "number_of_labels": None,
        "accuracy": None,
        "macro_f1": None,
        "weighted_f1": None,
    }
    if not METRICS_PATH.exists():
        return empty_metrics

    try:
        loaded = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_metrics

    return {
        "dataset_size": loaded.get("dataset_size"),
        "number_of_labels": loaded.get("number_of_labels"),
        "accuracy": loaded.get("accuracy"),
        "macro_f1": loaded.get("macro_f1"),
        "weighted_f1": loaded.get("weighted_f1"),
    }


async def _count(db: AsyncSession, stmt) -> int:
    """Run a scalar count query and normalize empty results to zero."""
    result = await db.execute(stmt)
    return int(result.scalar() or 0)


@router.get("/summary")
async def evaluation_summary(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("metrics:read")),
) -> dict[str, Any]:
    """Return model and system evaluation evidence for the demo dashboard."""
    metrics = _load_model_metrics()
    total_workflow_failures = await _count(db, select(func.count(WorkflowFailure.id)))
    total_fix_prs_created = await _count(
        db,
        select(func.count(WorkflowFailure.id)).where(WorkflowFailure.fix_pr_url.is_not(None)),
    )
    total_audit_logs = await _count(db, select(func.count(Execution.id)))
    total_approvals = await _count(db, select(func.count(ApprovalRequest.id)))

    return {
        **metrics,
        "total_workflow_failures": total_workflow_failures,
        "total_fix_prs_created": total_fix_prs_created,
        "total_audit_logs": total_audit_logs,
        "total_approvals": total_approvals,
    }
