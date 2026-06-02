"""CI/CD helper endpoints for repository analysis and workflow generation."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.core.security import require_permission
from app.schemas.schemas import CICDAnalyzeFilesRequest, CICDStackResponse, CICDWorkflowResponse
from app.services import audit_service
from app.services.repo_analyzer import detect_stack
from app.services.workflow_generator import WORKFLOW_PATH, generate_workflow

router = APIRouter()


@router.post("/analyze-files", response_model=CICDStackResponse)
async def analyze_files(
    request: CICDAnalyzeFilesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("cicd:read")),
):
    """Analyze a repository file list and recommend a CI workflow type."""
    actor = current_user.get("username") or current_user.get("sub") or "unknown"
    stack = detect_stack(request.files)
    try:
        await audit_service.log_repo_analysis(
            db,
            repo_full_name="uploaded-file-list",
            files_analyzed=len(request.files),
            detected_stack=stack,
            actor=actor,
            source="api",
        )
    except audit_service.AuditError as exc:
        await db.rollback()
        logger.warning("audit.cicd_analysis.skipped", error=str(exc))
    return stack


@router.post("/generate-workflow", response_model=CICDWorkflowResponse)
async def generate_ci_workflow(
    request: CICDAnalyzeFilesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("cicd:generate")),
):
    """Analyze a repository file list and generate GitHub Actions workflow YAML."""
    actor = current_user.get("username") or current_user.get("sub") or "unknown"
    stack = detect_stack(request.files)
    workflow_yaml = generate_workflow(stack)
    try:
        await audit_service.log_workflow_generation(
            db,
            repo_full_name="uploaded-file-list",
            detected_stack=stack,
            workflow_template_name=stack.get("recommended_workflow"),
            actor=actor,
            source="api",
        )
    except audit_service.AuditError as exc:
        await db.rollback()
        logger.warning("audit.workflow_generation.skipped", error=str(exc))
    return {
        "stack": stack,
        "path": WORKFLOW_PATH,
        "workflow_yaml": workflow_yaml,
    }
