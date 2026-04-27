"""HITL Approval endpoints."""
from uuid import UUID
from fastapi import APIRouter, Depends
from app.core.security import require_permission
from app.schemas.schemas import ApprovalDecision, ApprovalRequestOut

router = APIRouter()


@router.get("/", response_model=list[ApprovalRequestOut])
async def list_pending_approvals(
    current_user: dict = Depends(require_permission("logs:read")),
):
    """List all pending HITL approval requests."""
    # TODO: Query DB for pending ApprovalRequest records
    return []


@router.post("/{approval_id}/decide", status_code=200)
async def decide_approval(
    approval_id: UUID,
    decision: ApprovalDecision,
    current_user: dict = Depends(require_permission("deployments:production")),
):
    """
    Approve or reject a pending HITL approval request.
    Only operators and admins can approve high-risk actions.
    """
    # TODO: Update ApprovalRequest in DB, resume or cancel the pending execution
    action = "approved" if decision.approved else "rejected"
    return {
        "approval_id": str(approval_id),
        "status": action,
        "note": decision.note,
        "decided_by": current_user.get("username"),
    }
