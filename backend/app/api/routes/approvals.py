"""
HITL Approval endpoints.

Flow
----
1. Agent detects HIGH/CRITICAL risk → calls `create_approval_request()` helper.
2. Record lands in `approval_requests` table with status="pending".
3. Operator polls GET /api/v1/approvals/ to see pending items.
4. Operator calls POST /api/v1/approvals/{id}/decide with approved=true|false.
5. If approved, we execute the tool and log an Execution record.
   If rejected, we mark the request "rejected" and log a cancelled Execution.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.core.security import require_permission
from app.models.models import ApprovalRequest, Execution
from app.schemas.schemas import ApprovalDecision, ApprovalRequestOut

router = APIRouter()


# ── Helper used by the agent ──────────────────────────────────────────────────

async def create_approval_request(
    *,
    db: AsyncSession,
    session_id: str,
    requested_by: str,
    tool_name: str,
    tool_input: dict,
    action: str,
    risk_level: str,
    summary: str,
    timeout_seconds: int = 300,
) -> ApprovalRequest:
    """
    Persist a pending approval and return the record.

    Called by the agent when it classifies an action as HIGH or CRITICAL risk.
    """
    from datetime import timedelta
    expires = datetime.now(tz=timezone.utc) + timedelta(seconds=timeout_seconds)
    record = ApprovalRequest(
        id=str(uuid.uuid4()),
        session_id=session_id,
        requested_by=requested_by,
        tool_name=tool_name,
        tool_input=json.dumps(tool_input),
        action=action,
        risk_level=risk_level,
        summary=summary,
        status="pending",
        expires_at=expires,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    logger.info(
        "hitl.approval.created",
        approval_id=record.id,
        tool=tool_name,
        risk=risk_level,
        user=requested_by,
    )
    return record


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[ApprovalRequestOut])
async def list_pending_approvals(
    status_filter: Optional[str] = "pending",
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("logs:read")),
):
    """List approval requests (default: pending only)."""
    stmt = select(ApprovalRequest).order_by(ApprovalRequest.created_at.desc())
    if status_filter:
        stmt = stmt.where(ApprovalRequest.status == status_filter)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{approval_id}", response_model=ApprovalRequestOut)
async def get_approval(
    approval_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("logs:read")),
):
    """Fetch a single approval request by ID."""
    record = await db.get(ApprovalRequest, str(approval_id))
    if not record:
        raise HTTPException(status_code=404, detail="Approval request not found.")
    return record


@router.post("/{approval_id}/decide", status_code=200)
async def decide_approval(
    approval_id: UUID,
    decision: ApprovalDecision,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("deployments:production")),
):
    """
    Approve or reject a pending HITL approval request.
    Only operators and admins can approve high-risk actions.

    On approval  → the tool is executed immediately and an Execution record is created.
    On rejection → the request is marked rejected and a cancelled Execution is logged.
    """
    record: Optional[ApprovalRequest] = await db.get(ApprovalRequest, str(approval_id))
    if not record:
        raise HTTPException(status_code=404, detail="Approval request not found.")

    if record.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Approval request is already '{record.status}' — cannot decide again.",
        )

    # Check expiry
    if record.expires_at:
        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
    else:
        expires_at = None

    if expires_at and datetime.now(tz=timezone.utc) > expires_at:
        record.status = "timed_out"
        await db.flush()
        raise HTTPException(status_code=410, detail="Approval request has expired.")

    now = datetime.now(tz=timezone.utc)
    decider = current_user.get("username", "unknown")

    if decision.approved:
        # ── Execute the tool ──────────────────────────────────────────────────
        tool_input = json.loads(record.tool_input)
        exec_details, exec_status = _dispatch_tool(record.tool_name, tool_input)

        record.status = "approved"
        record.decided_by = decider
        record.decision_note = decision.note
        record.decided_at = now

        execution = Execution(
            id=str(uuid.uuid4()),
            approval_id=record.id,
            session_id=record.session_id,
            requested_by=record.requested_by,
            tool_name=record.tool_name,
            tool_input=record.tool_input,
            status=exec_status,
            summary=f"Approved by {decider}. {record.summary}",
            details=exec_details,
            source="hitl",
            started_at=now,
            completed_at=datetime.now(tz=timezone.utc),
        )
        db.add(execution)
        await db.flush()

        logger.info(
            "hitl.approval.approved",
            approval_id=str(approval_id),
            tool=record.tool_name,
            decided_by=decider,
            exec_status=exec_status,
        )
        return {
            "approval_id": str(approval_id),
            "status": "approved",
            "note": decision.note,
            "decided_by": decider,
            "execution_id": execution.id,
            "execution_status": exec_status,
            "execution_details": exec_details,
        }
    else:
        # ── Reject / cancel ───────────────────────────────────────────────────
        record.status = "rejected"
        record.decided_by = decider
        record.decision_note = decision.note
        record.decided_at = now

        execution = Execution(
            id=str(uuid.uuid4()),
            approval_id=record.id,
            session_id=record.session_id,
            requested_by=record.requested_by,
            tool_name=record.tool_name,
            tool_input=record.tool_input,
            status="cancelled",
            summary=f"Rejected by {decider}. {record.summary}",
            details=f"Rejection note: {decision.note or '(none)'}",
            source="hitl",
            started_at=now,
            completed_at=now,
        )
        db.add(execution)
        await db.flush()

        logger.info(
            "hitl.approval.rejected",
            approval_id=str(approval_id),
            tool=record.tool_name,
            decided_by=decider,
        )
        return {
            "approval_id": str(approval_id),
            "status": "rejected",
            "note": decision.note,
            "decided_by": decider,
        }


def _dispatch_tool(tool_name: str, tool_input: dict) -> tuple[str, str]:
    """
    Execute the approved tool and return (details_string, status_string).

    Extend this dispatcher as new tools are added to tools_registry.
    """
    try:
        if tool_name == "docker_restart_container":
            from app.tools.docker_tool import restart_container
            details = restart_container(tool_input.get("container_name", ""))
        elif tool_name == "docker_stop_container":
            from app.tools.docker_tool import stop_container
            details = stop_container(tool_input.get("container_name", ""))
        elif tool_name == "docker_start_container":
            from app.tools.docker_tool import start_container
            details = start_container(tool_input.get("container_name", ""))
        elif tool_name == "docker_run_container":
            from app.tools.docker_tool import run_container
            details = run_container(**tool_input)
        elif tool_name == "github_trigger_workflow":
            from app.tools.github_tool import trigger_workflow
            details = trigger_workflow(**tool_input)
        elif tool_name == "execute_shell_command":
            from app.tools.shell_tool import execute_safe_shell_command
            details = execute_safe_shell_command(tool_input.get("command", ""))
        else:
            details = f"Unknown tool '{tool_name}' — no dispatcher registered."
            return details, "failed"
        return details, "completed"
    except Exception as exc:
        logger.error("hitl.dispatch_tool.error", tool=tool_name, error=str(exc))
        return f"Tool execution error: {exc}", "failed"
