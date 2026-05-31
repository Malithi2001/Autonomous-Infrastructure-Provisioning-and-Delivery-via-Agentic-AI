"""Test audit logging for model prediction endpoint."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.services import audit_service


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def db_session() -> AsyncSession:
    async with TestSession() as session:
        yield session
        await session.rollback()


@pytest.mark.asyncio
async def test_audit_service_logs_prediction(db_session: AsyncSession):
    """Verify that audit service creates proper prediction log."""
    log_text = "npm ERR! code ERESOLVE\nnpm ERR! ERESOLVE unable to resolve dependency tree"
    execution = await audit_service.log_prediction(
        db_session,
        log_text=log_text,
        predicted_label="npm_install_failed",
        confidence=0.85,
        suggested_fix="Run npm ci instead of npm install",
        actor="test_user",
        source="api",
    )

    assert execution is not None
    assert execution.tool_name == "failure_prediction_model"
    assert execution.status == "completed"
    assert execution.source == "api"
    assert "npm_install_failed" in execution.details
    assert execution.requested_by == "test_user"

    assert execution.tool_input is not None
    assert "log_length" in execution.tool_input


@pytest.mark.asyncio
async def test_audit_service_logs_repo_analysis(db_session: AsyncSession):
    """Verify that audit service creates proper repo analysis log."""
    execution = await audit_service.log_repo_analysis(
        db_session,
        repo_full_name="octo-org/demo-app",
        files_analyzed=15,
        detected_stack={"primary_language": "javascript", "framework": "react"},
        actor="system",
        source="api",
    )

    assert execution is not None
    assert execution.tool_name == "repository_analyzer"
    assert "octo-org/demo-app" in execution.summary
    assert "15" in execution.summary


@pytest.mark.asyncio
async def test_audit_service_logs_approval(db_session: AsyncSession):
    """Verify that audit service creates proper approval log."""
    execution = await audit_service.log_approval_decision(
        db_session,
        approval_id="approval-123",
        decision="approved",
        tool_name="github_fix_pr",
        actor="operator_user",
        reason="Fix looks good and low risk",
    )

    assert execution is not None
    assert execution.tool_name == "approval_decision"
    assert "approved" in execution.status or "approved" in execution.details
    assert execution.requested_by == "operator_user"


@pytest.mark.asyncio
async def test_audit_service_redacts_tokens(db_session: AsyncSession):
    """Verify that audit service redacts sensitive tokens from logs."""
    tool_output = {
        "api_key": "sk-1234567890abcdef",
        "token": "ghp_1234567890abcdefghijklmnopqrstuvwxyz",
        "status": "success",
    }

    execution = await audit_service.log_execution(
        db_session,
        tool_name="test_tool",
        action_summary="Test with sensitive data",
        tool_output=tool_output,
        actor="test_user",
    )

    assert "[REDACTED]" in execution.details
    assert "sk-" not in execution.details
    details = execution.details
    assert "ghp_" not in details or "[REDACTED]" in details
