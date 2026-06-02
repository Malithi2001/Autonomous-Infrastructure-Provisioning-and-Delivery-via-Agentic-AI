"""Tests for workflow failure diagnosis persistence and API routes."""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.routes import workflow_failures
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.models.models import ApprovalRequest
from app.services.workflow_failure_service import create_workflow_failure, list_workflow_failures


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


def _build_test_app() -> FastAPI:
    test_app = FastAPI(title="Workflow Failure Test App")
    test_app.include_router(workflow_failures.router, prefix="/api/v1/workflow-failures")
    return test_app


app = _build_test_app()


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


@pytest_asyncio.fixture(autouse=True)
async def override_db(db_session: AsyncSession):
    async def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def _auth_headers(role: str = "developer") -> dict[str, str]:
    token = create_access_token(
        {
            "sub": str(uuid.uuid4()),
            "username": "workflow-failure-test-user",
            "role": role,
        }
    )
    return {"Authorization": f"Bearer {token}"}


async def _create_failure(db_session: AsyncSession):
    return await create_workflow_failure(
        db_session,
        repo_full_name="octo-org/demo-app",
        workflow_run_id=123456789,
        workflow_name="CI",
        branch="feature/demo",
        conclusion="failure",
        workflow_url="https://github.com/octo-org/demo-app/actions/runs/123456789",
        log_excerpt="npm ERR! Missing script: test",
        predicted_label="npm_missing_test_script",
        confidence=0.82,
        suggested_fix="Add a test script to package.json.",
        recommendation={
            "summary": "The CI job ran npm test, but package.json does not define a test script.",
            "root_cause": "Missing scripts.test.",
            "safe_fix_available": True,
            "recommended_changes": ["Add scripts.test to package.json."],
            "risk_level": "low",
            "requires_approval": False,
        },
        status="diagnosed",
    )


@pytest.mark.asyncio
async def test_create_and_list_workflow_failures_service(db_session: AsyncSession):
    record = await _create_failure(db_session)

    records = await list_workflow_failures(db_session)

    assert len(records) == 1
    assert records[0].id == record.id
    assert records[0].repo_full_name == "octo-org/demo-app"
    assert records[0].predicted_label == "npm_missing_test_script"


@pytest.mark.asyncio
async def test_list_workflow_failures_endpoint(client: TestClient, db_session: AsyncSession):
    record = await _create_failure(db_session)

    response = client.get("/api/v1/workflow-failures", headers=_auth_headers())

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == record.id
    assert body[0]["repo_full_name"] == "octo-org/demo-app"
    assert body[0]["workflow_run_id"] == 123456789
    assert body[0]["workflow_name"] == "CI"
    assert body[0]["branch"] == "feature/demo"
    assert body[0]["conclusion"] == "failure"
    assert body[0]["predicted_label"] == "npm_missing_test_script"
    assert body[0]["confidence"] == 0.82
    assert body[0]["recommendation"]["risk_level"] == "low"
    assert body[0]["fix_pr_url"] is None
    assert body[0]["status"] == "diagnosed"


@pytest.mark.asyncio
async def test_get_workflow_failure_endpoint(client: TestClient, db_session: AsyncSession):
    record = await _create_failure(db_session)

    response = client.get(f"/api/v1/workflow-failures/{record.id}", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json()["id"] == record.id


@pytest.mark.asyncio
async def test_create_fix_pr_endpoint_requires_write_permission(client: TestClient, db_session: AsyncSession):
    record = await _create_failure(db_session)

    response = client.post(f"/api/v1/workflow-failures/{record.id}/create-fix-pr", headers=_auth_headers("developer"))

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_fix_pr_endpoint_returns_service_result(monkeypatch, client: TestClient, db_session: AsyncSession):
    record = await _create_failure(db_session)

    async def _fake_create_fix_pr_for_failure(db, failure_id, current_user):
        assert failure_id == record.id
        assert current_user["role"] == "operator"
        return {
            "workflow_failure_id": record.id,
            "repo_full_name": "octo-org/demo-app",
            "status": "fix_pr_created",
            "branch": "ai-cicd/fix-123456789",
            "workflow_path": ".github/workflows/ci.yml",
            "pull_request_url": "https://github.com/octo-org/demo-app/pull/22",
            "message": "Changed npm test to npm test --if-present in the workflow.",
            "recommendation": record.recommendation,
        }

    monkeypatch.setattr(workflow_failures, "create_fix_pr_for_failure", _fake_create_fix_pr_for_failure)

    response = client.post(f"/api/v1/workflow-failures/{record.id}/create-fix-pr", headers=_auth_headers("operator"))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "fix_pr_created"
    assert body["branch"] == "ai-cicd/fix-123456789"
    assert body["pull_request_url"] == "https://github.com/octo-org/demo-app/pull/22"


@pytest.mark.asyncio
async def test_create_fix_pr_endpoint_creates_approval_for_medium_risk(
    client: TestClient,
    db_session: AsyncSession,
):
    record = await create_workflow_failure(
        db_session,
        repo_full_name="octo-org/demo-app",
        workflow_run_id=4321,
        workflow_name="CI",
        conclusion="failure",
        predicted_label="wrong_runtime_version",
        suggested_fix="Update the workflow runtime version.",
        recommendation={
            "summary": "Runtime version mismatch.",
            "root_cause": "CI selected an incompatible runtime.",
            "safe_fix_available": True,
            "recommended_changes": ["Update setup-node or setup-python to the required version."],
            "risk_level": "medium",
            "requires_approval": True,
        },
        status="diagnosed",
    )

    response = client.post(f"/api/v1/workflow-failures/{record.id}/create-fix-pr", headers=_auth_headers("operator"))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approval_required"
    assert body["approval_id"]
    assert body["approval_details"]["repository"] == "octo-org/demo-app"
    assert body["approval_details"]["workflow_run_id"] == 4321
    assert body["approval_details"]["risk_level"] == "medium"
    await db_session.refresh(record)
    assert record.status == "approval_pending"

    approval_result = await db_session.execute(select(ApprovalRequest).where(ApprovalRequest.id == body["approval_id"]))
    approval = approval_result.scalar_one()
    assert approval.status == "pending"
    assert approval.tool_name == "github_create_fix_pr"


def test_workflow_failures_endpoint_requires_auth(client: TestClient):
    response = client.get("/api/v1/workflow-failures")

    assert response.status_code in (401, 403)


def test_get_workflow_failure_endpoint_returns_404(client: TestClient):
    response = client.get(f"/api/v1/workflow-failures/{uuid.uuid4()}", headers=_auth_headers())

    assert response.status_code == 404
