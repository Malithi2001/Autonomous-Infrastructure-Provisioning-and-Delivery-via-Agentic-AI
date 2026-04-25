"""Webhook endpoints for GitHub Actions and other CI/CD integrations."""
import hashlib
import hmac

from fastapi import APIRouter, Header, HTTPException, Request

from app.core.config import settings
from app.core.logging import logger

router = APIRouter()


def _verify_github_signature(payload: bytes, signature: str) -> bool:
    """Verify the GitHub webhook HMAC-SHA256 signature."""
    if not settings.GITHUB_WEBHOOK_SECRET:
        return True  # Skip verification in dev if secret not set
    expected = "sha256=" + hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None),
):
    """
    Receive GitHub Actions webhook events.
    Used to trigger self-healing workflows on pipeline failures.
    """
    body = await request.body()

    if x_hub_signature_256 and not _verify_github_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    payload = await request.json()
    event = x_github_event or "unknown"

    logger.info("webhook.github.received", event=event)

    if event == "workflow_run" and payload.get("action") == "completed":
        conclusion = payload.get("workflow_run", {}).get("conclusion")
        if conclusion == "failure":
            logger.warning(
                "webhook.github.workflow_failed",
                repo=payload.get("repository", {}).get("full_name"),
                workflow=payload.get("workflow_run", {}).get("name"),
            )
            # TODO: Trigger agent self-healing workflow

    return {"received": True, "event": event}
