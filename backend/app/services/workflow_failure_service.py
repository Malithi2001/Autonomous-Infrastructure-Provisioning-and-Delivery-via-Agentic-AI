"""Persistence helpers for GitHub Actions workflow failure diagnoses."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import WorkflowFailure


async def create_workflow_failure(
    db: AsyncSession,
    *,
    repo_full_name: str,
    workflow_run_id: int,
    workflow_name: str | None = None,
    branch: str | None = None,
    conclusion: str = "failure",
    workflow_url: str | None = None,
    log_excerpt: str | None = None,
    predicted_label: str | None = None,
    confidence: float | None = None,
    suggested_fix: str | None = None,
    recommendation: dict[str, Any] | None = None,
    fix_pr_url: str | None = None,
    status: str = "diagnosed",
) -> WorkflowFailure:
    """Create and flush a workflow failure diagnosis record."""
    record = WorkflowFailure(
        repo_full_name=repo_full_name,
        workflow_run_id=workflow_run_id,
        workflow_name=workflow_name,
        branch=branch,
        conclusion=conclusion,
        workflow_url=workflow_url,
        log_excerpt=log_excerpt,
        predicted_label=predicted_label,
        confidence=confidence,
        suggested_fix=suggested_fix,
        recommendation_json=json.dumps(recommendation, ensure_ascii=False) if recommendation else None,
        fix_pr_url=fix_pr_url,
        status=status,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


async def list_workflow_failures(
    db: AsyncSession,
    *,
    limit: int = 50,
    repo_full_name: str | None = None,
    status: str | None = None,
) -> list[WorkflowFailure]:
    """List recent workflow failure diagnoses."""
    stmt = select(WorkflowFailure).order_by(WorkflowFailure.created_at.desc()).limit(min(limit, 200))
    if repo_full_name:
        stmt = stmt.where(WorkflowFailure.repo_full_name == repo_full_name)
    if status:
        stmt = stmt.where(WorkflowFailure.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_workflow_failure(db: AsyncSession, failure_id: str) -> WorkflowFailure | None:
    """Fetch a workflow failure diagnosis by id."""
    return await db.get(WorkflowFailure, failure_id)


def workflow_failure_values(
    *,
    repo_full_name: str | None,
    workflow_run_id: Any,
    workflow_name: str | None,
    branch: str | None,
    conclusion: str | None,
    workflow_url: str | None,
    log_excerpt: str | None,
    prediction: dict[str, Any] | None,
    error: str | None,
) -> dict[str, Any]:
    """Build normalized values for storing a webhook diagnosis."""
    prediction = prediction or {}
    return {
        "repo_full_name": repo_full_name or "unknown",
        "workflow_run_id": int(workflow_run_id or 0),
        "workflow_name": workflow_name,
        "branch": branch,
        "conclusion": conclusion or "failure",
        "workflow_url": workflow_url,
        "log_excerpt": log_excerpt,
        "predicted_label": prediction.get("label"),
        "confidence": prediction.get("confidence"),
        "suggested_fix": prediction.get("suggested_fix"),
        "recommendation": prediction.get("recommendation"),
        "fix_pr_url": None,
        "status": "diagnosis_failed" if error else "diagnosed",
    }
