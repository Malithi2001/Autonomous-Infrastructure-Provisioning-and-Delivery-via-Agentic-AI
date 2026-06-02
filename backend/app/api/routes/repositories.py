"""Repository inspection endpoints."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import require_permission
from app.models.models import ApprovalRequest, Execution
from app.schemas.schemas import (
    RepositoryInstallationOut,
    RepositoryScanRequest,
    RepositoryScanResponse,
    RepositoryWorkflowPRRequest,
    RepositoryWorkflowPRResponse,
)
from app.services import audit_service
from app.services.github_app_service import (
    GitHubAppError,
    get_installation_access_token,
    get_installation_for_repo,
    list_installed_repositories,
)
from app.services.cicd_readiness_service import assess_cicd_readiness
from app.services.repo_analyzer import detect_stack
from app.tools.github_tool import GitHubToolError, create_workflow_pr, get_repository_analysis_inputs

router = APIRouter()


async def _installation_token_for_repo(db: AsyncSession, repo_full_name: str) -> str | None:
    """Return a GitHub App installation token for installed repos, or None for PAT fallback."""
    installation = await get_installation_for_repo(db, repo_full_name)
    if not installation:
        return None
    return get_installation_access_token(installation.installation_id)


@router.get("/installed", response_model=list[RepositoryInstallationOut])
async def installed_repositories(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("repositories:read")),
):
    """List repositories installed through the GitHub App."""
    return await list_installed_repositories(db)


@router.post("/scan", response_model=RepositoryScanResponse)
async def scan_repository(
    request: RepositoryScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("repositories:read")),
):
    """Fetch a GitHub repository tree and analyze its CI/CD stack."""
    try:
        token = await _installation_token_for_repo(db, request.repo_full_name)
        analysis = (
            get_repository_analysis_inputs(request.repo_full_name, request.branch, token=token)
            if token
            else get_repository_analysis_inputs(request.repo_full_name, request.branch)
        )
        files = analysis["files"]
        stack = detect_stack(analysis["analysis_inputs"])
        readiness = assess_cicd_readiness(files, stack)
        await audit_service.log_repo_analysis(
            db,
            repo_full_name=request.repo_full_name,
            files_analyzed=len(files),
            detected_stack=stack,
            actor=current_user.get("username") or current_user.get("sub") or "unknown",
            source="api",
        )
    except (GitHubToolError, GitHubAppError) as exc:
        await audit_service.log_execution(
            db,
            tool_name="repository_analyzer",
            action_summary=f"Failed to analyze repository {request.repo_full_name}",
            status="failed",
            actor=current_user.get("username") or current_user.get("sub") or "unknown",
            tool_input={"repo": request.repo_full_name, "branch": request.branch},
            tool_output={},
            error=str(exc),
            source="api",
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "repo_full_name": request.repo_full_name,
        "files": files,
        "stack": stack,
        "readiness": readiness,
    }


@router.post(
    "/create-workflow-pr",
    response_model=RepositoryWorkflowPRResponse,
    response_model_exclude_none=True,
)
async def create_repository_workflow_pr(
    request: RepositoryWorkflowPRRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("repositories:write")),
):
    """Create an AI-generated GitHub Actions workflow pull request."""
    actor = current_user.get("username", current_user.get("sub", "unknown"))
    now = datetime.now(tz=timezone.utc)
    execution = Execution(
        id=str(uuid.uuid4()),
        requested_by=actor,
        tool_name="github_create_workflow_pr",
        tool_input=json.dumps(
            {
                "repo_full_name": request.repo_full_name,
                "overwrite_existing_workflow": request.overwrite_existing_workflow,
            },
            ensure_ascii=False,
        ),
        status="running",
        summary=f"Create AI-generated workflow PR for {request.repo_full_name}",
        source="api",
        started_at=now,
    )
    db.add(execution)
    await db.flush()

    if settings.ENABLE_HITL:
        approval = ApprovalRequest(
            id=str(uuid.uuid4()),
            session_id=str(uuid.uuid4()),
            requested_by=actor,
            tool_name="github_create_workflow_pr",
            tool_input=execution.tool_input,
            action="Create GitHub Actions workflow pull request",
            risk_level="medium",
            summary=f"Approve workflow PR creation for {request.repo_full_name}.",
            status="pending",
            expires_at=now + timedelta(seconds=settings.HITL_APPROVAL_TIMEOUT_SECONDS),
        )
        db.add(approval)
        await db.flush()
        await db.refresh(approval)

        execution.status = "pending"
        execution.approval_id = approval.id
        execution.summary = f"Approval required before creating workflow PR for {request.repo_full_name}"
        execution.details = json.dumps(
            {
                "approval_required": True,
                "approval_id": approval.id,
                "repo_full_name": request.repo_full_name,
                "overwrite_existing_workflow": request.overwrite_existing_workflow,
            },
            ensure_ascii=False,
        )
        await audit_service.log_execution(
            db,
            tool_name="github_workflow_pr",
            action_summary=f"Approval required before creating workflow PR for {request.repo_full_name}",
            status="pending",
            actor=actor,
            tool_input={
                "repo": request.repo_full_name,
                "overwrite_existing_workflow": request.overwrite_existing_workflow,
            },
            tool_output={"approval_id": approval.id},
            session_id=approval.session_id,
            source="api",
        )
        return {
            "repo_full_name": request.repo_full_name,
            "status": "approval_required",
            "approval_required": True,
            "approval_id": approval.id,
            "message": "Human approval is required before creating the workflow pull request.",
        }

    try:
        token = await _installation_token_for_repo(db, request.repo_full_name)
        result = (
            create_workflow_pr(
                request.repo_full_name,
                overwrite_existing_workflow=request.overwrite_existing_workflow,
                token=token,
            )
            if token
            else create_workflow_pr(
                request.repo_full_name,
                overwrite_existing_workflow=request.overwrite_existing_workflow,
            )
        )
    except (GitHubToolError, GitHubAppError) as exc:
        execution.status = "failed"
        execution.summary = f"Failed to create AI-generated workflow PR for {request.repo_full_name}"
        execution.details = json.dumps({"error": str(exc)}, ensure_ascii=False)
        execution.completed_at = datetime.now(tz=timezone.utc)
        await audit_service.log_workflow_pr_creation(
            db,
            repo_full_name=request.repo_full_name,
            branch="",
            pull_request_url=None,
            status="failed",
            error=str(exc),
            actor=actor,
            source="api",
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    response = {
        "repo_full_name": result["repo_full_name"],
        "detected_stack": result["detected_stack"],
        "branch": result["branch"],
        "workflow_path": result["workflow_path"],
        "pull_request_url": result["pull_request_url"],
    }
    execution.status = "completed"
    execution.summary = (
        f"Created AI-generated workflow PR for {result['repo_full_name']}: "
        f"{result['pull_request_url']}"
    )
    execution.details = json.dumps(response, ensure_ascii=False)
    execution.completed_at = datetime.now(tz=timezone.utc)
    await audit_service.log_workflow_pr_creation(
        db,
        repo_full_name=result["repo_full_name"],
        branch=result["branch"],
        pull_request_url=result["pull_request_url"],
        actor=actor,
        source="api",
    )
    return response
