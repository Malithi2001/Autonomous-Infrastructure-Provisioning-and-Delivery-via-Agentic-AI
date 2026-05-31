"""Webhook endpoints for GitHub Actions and other CI/CD integrations."""
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.models.models import Execution
from app.services import audit_service
from app.services import failure_prediction_service
from app.services.failure_prediction_service import FailurePredictionError, FailurePredictionUnavailable
from app.services.github_app_service import (
    GitHubAppError,
    get_installation_access_token,
    mark_repository_removed,
    upsert_repository_installation,
    verify_webhook_signature,
)
from app.services.workflow_failure_service import create_workflow_failure, workflow_failure_values
from app.tools.github_tool import GitHubToolError, download_workflow_logs

router = APIRouter()
LOG_EXCERPT_LIMIT = 1500


@router.post("/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Receive GitHub Actions webhook events.
    Used to trigger self-healing workflows on pipeline failures.
    """
    body = await request.body()

    if not verify_webhook_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    payload = await request.json()
    event = x_github_event or "unknown"

    logger.info("webhook.github.received", github_event=event)

    if event == "installation":
        await _handle_installation_event(payload, db)
    elif event == "installation_repositories":
        await _handle_installation_repositories_event(payload, db)
    elif event == "workflow_run" and payload.get("action") == "completed":
        conclusion = payload.get("workflow_run", {}).get("conclusion")
        if conclusion == "failure":
            try:
                await _handle_failed_workflow_run(payload, db)
            except Exception as exc:
                logger.error(
                    "webhook.github.workflow_failed.unhandled_error",
                    error_type=exc.__class__.__name__,
                )

    return {"received": True, "event": event}


async def _handle_installation_event(payload: dict[str, Any], db: AsyncSession) -> None:
    """Store repositories granted or removed by a GitHub App installation event."""
    action = payload.get("action")
    installation_id = (payload.get("installation") or {}).get("id")
    repositories = payload.get("repositories") or []
    if not installation_id:
        logger.warning("webhook.github.installation.missing_installation_id", action=action)
        return

    status = "active" if action in {"created", "unsuspend", "new_permissions_accepted"} else "removed"
    if action in {"deleted", "suspend"}:
        status = "removed"

    for repository in repositories:
        if not isinstance(repository, dict):
            continue
        try:
            await upsert_repository_installation(
                db,
                installation_id=installation_id,
                repository=repository,
                status=status,
            )
        except GitHubAppError as exc:
            logger.warning("webhook.github.installation.repository_skipped", error=str(exc))
    await db.flush()


async def _handle_installation_repositories_event(payload: dict[str, Any], db: AsyncSession) -> None:
    """Store repositories added to or removed from a GitHub App installation."""
    installation_id = (payload.get("installation") or {}).get("id")
    if not installation_id:
        logger.warning("webhook.github.installation_repositories.missing_installation_id")
        return

    for repository in payload.get("repositories_added") or []:
        if isinstance(repository, dict):
            await upsert_repository_installation(
                db,
                installation_id=installation_id,
                repository=repository,
                status="active",
            )
    for repository in payload.get("repositories_removed") or []:
        if isinstance(repository, dict):
            await mark_repository_removed(
                db,
                installation_id=installation_id,
                repository=repository,
            )
    await db.flush()


async def _handle_failed_workflow_run(payload: dict[str, Any], db: AsyncSession) -> None:
    """Predict a root cause for failed GitHub Actions workflow runs."""
    repository = payload.get("repository") or {}
    workflow_run = payload.get("workflow_run") or {}

    repo_full_name = repository.get("full_name")
    workflow_run_id = workflow_run.get("id")
    workflow_name = workflow_run.get("name")
    branch = workflow_run.get("head_branch")
    conclusion = workflow_run.get("conclusion") or "failure"
    workflow_url = workflow_run.get("html_url")
    installation_id = (payload.get("installation") or {}).get("id")

    prediction: dict[str, Any] | None = None
    status = "completed"
    error: str | None = None
    log_source = "github_actions"
    log_text = ""
    log_excerpt = ""

    try:
        if not repo_full_name:
            raise GitHubToolError("Webhook payload does not include repository full_name.")
        if not workflow_run_id:
            raise GitHubToolError("Webhook payload does not include workflow_run id.")

        token = get_installation_access_token(installation_id) if installation_id else None
        if token:
            log_text = download_workflow_logs(repo_full_name, int(workflow_run_id), token=token)
        else:
            log_text = download_workflow_logs(repo_full_name, int(workflow_run_id))
        await audit_service.log_log_download(
            db,
            repo_full_name=repo_full_name,
            run_id=int(workflow_run_id),
            log_length=len(log_text),
            actor="github_webhook",
            source="webhook_aux",
        )
        log_excerpt = _log_excerpt(log_text)
        prediction = failure_prediction_service.predict_failure(log_text)
        if prediction.get("recommendation"):
            await audit_service.log_fix_recommendation(
                db,
                failure_label=prediction.get("label", "unknown_failure"),
                recommendation=prediction.get("recommendation"),
                actor="github_webhook",
                source="webhook_aux",
            )
        logger.warning(
            "webhook.github.workflow_failed.predicted",
            repo=repo_full_name,
            workflow_run_id=workflow_run_id,
            workflow=workflow_name,
            branch=branch,
            html_url=workflow_url,
            failure_category=prediction.get("label"),
            confidence=prediction.get("confidence"),
            suggested_fix=prediction.get("suggested_fix"),
            log_excerpt=log_excerpt,
        )
    except (GitHubToolError, GitHubAppError, FailurePredictionUnavailable, FailurePredictionError) as exc:
        status = "failed"
        error = str(exc)
        if repo_full_name and workflow_run_id and isinstance(exc, (GitHubToolError, GitHubAppError)):
            await audit_service.log_log_download(
                db,
                repo_full_name=repo_full_name,
                run_id=int(workflow_run_id),
                log_length=len(log_text),
                status="failed",
                error=error,
                actor="github_webhook",
                source="webhook_aux",
            )
        logger.error(
            "webhook.github.workflow_failed.prediction_error",
            repo=repo_full_name,
            workflow_run_id=workflow_run_id,
            workflow=workflow_name,
            branch=branch,
            html_url=workflow_url,
            error=error,
        )
    except Exception as exc:
        status = "failed"
        error = "Unexpected webhook failure diagnosis error."
        logger.error(
            "webhook.github.workflow_failed.unexpected_prediction_error",
            repo=repo_full_name,
            workflow_run_id=workflow_run_id,
            workflow=workflow_name,
            branch=branch,
            html_url=workflow_url,
            error_type=exc.__class__.__name__,
        )

    now = datetime.now(tz=timezone.utc)
    workflow_failure = await create_workflow_failure(
        db,
        **workflow_failure_values(
            repo_full_name=repo_full_name,
            workflow_run_id=workflow_run_id,
            workflow_name=workflow_name,
            branch=branch,
            conclusion=conclusion,
            workflow_url=workflow_url,
            log_excerpt=log_excerpt,
            prediction=prediction,
            error=error,
        ),
    )
    db.add(
        Execution(
            id=str(uuid.uuid4()),
            requested_by="github_webhook",
            tool_name="failure_prediction_model",
            tool_input=json.dumps(
                {
                    "repo": repo_full_name,
                    "workflow_run_id": workflow_run_id,
                    "workflow": workflow_name,
                    "branch": branch,
                    "conclusion": conclusion,
                    "html_url": workflow_url,
                    "workflow_failure_id": workflow_failure.id,
                    "log_source": log_source,
                    "log_chars": len(log_text),
                    "log_excerpt": log_excerpt,
                },
                ensure_ascii=False,
            ),
            status=status,
            summary=_prediction_summary(repo_full_name, workflow_name, branch, prediction, error),
            details=json.dumps(
                {
                    "repo": repo_full_name,
                    "workflow_run_id": workflow_run_id,
                    "workflow": workflow_name,
                    "branch": branch,
                    "conclusion": conclusion,
                    "html_url": workflow_url,
                    "workflow_failure_id": workflow_failure.id,
                    "prediction": prediction,
                    "predicted_label": prediction.get("label") if prediction else None,
                    "confidence": prediction.get("confidence") if prediction else None,
                    "suggested_fix": prediction.get("suggested_fix") if prediction else None,
                    "recommendation": prediction.get("recommendation") if prediction else None,
                    "error": error,
                    "log_source": log_source,
                    "log_chars": len(log_text),
                    "log_excerpt": log_excerpt,
                },
                ensure_ascii=False,
            ),
            source="webhook",
            started_at=now,
            completed_at=now,
        )
    )
    await db.flush()


def _log_excerpt(log_text: str, limit: int = LOG_EXCERPT_LIMIT) -> str:
    """Return a compact log excerpt suitable for audit records."""
    cleaned = " ".join((log_text or "").split())
    return cleaned[:limit]


def _prediction_summary(
    repo_full_name: str | None,
    workflow_name: str | None,
    branch: str | None,
    prediction: dict[str, Any] | None,
    error: str | None,
) -> str:
    prefix = f"GitHub workflow failed for {repo_full_name or 'unknown repo'}"
    if workflow_name:
        prefix += f" / {workflow_name}"
    if branch:
        prefix += f" on {branch}"
    if error:
        return f"{prefix}. Failure prediction unavailable: {error}"
    if not prediction:
        return f"{prefix}. Failure prediction unavailable."
    return (
        f"{prefix}. Predicted {prediction.get('label')} "
        f"(confidence={prediction.get('confidence')}). "
        f"Suggested fix: {prediction.get('suggested_fix')}"
    )
