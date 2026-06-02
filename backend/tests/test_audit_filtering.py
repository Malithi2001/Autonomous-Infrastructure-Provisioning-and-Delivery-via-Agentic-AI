"""Test audit filtering API."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.routes import executions
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.models.models import Execution


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


def _build_test_app() -> FastAPI:
    test_app = FastAPI(title="Audit Filtering Test App")
    test_app.include_router(executions.router, prefix="/api/v1/audit")
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


def _auth_headers(role: str = "operator") -> dict[str, str]:
    token = create_access_token(
        {
            "sub": str(uuid.uuid4()),
            "username": "audit-test-user",
            "role": role,
        }
    )
    return {"Authorization": f"Bearer {token}"}


async def _seed_execution(
    db_session: AsyncSession,
    *,
    tool_name: str,
    status: str = "completed",
    summary: str | None = None,
    started_at: datetime | None = None,
) -> Execution:
    now = started_at or datetime.now(tz=timezone.utc)
    execution = Execution(
        id=str(uuid.uuid4()),
        session_id=f"session-{tool_name}-{uuid.uuid4()}",
        requested_by="test_user",
        tool_name=tool_name,
        tool_input="{}",
        status=status,
        summary=summary or f"Test {tool_name}",
        details="{}",
        source="api",
        started_at=now,
        completed_at=now,
    )
    db_session.add(execution)
    await db_session.flush()
    return execution


@pytest.mark.asyncio
async def test_executions_filter_by_tool(db_session: AsyncSession):
    await _seed_execution(db_session, tool_name="failure_prediction_model")
    await _seed_execution(db_session, tool_name="github_workflow_pr")
    await _seed_execution(db_session, tool_name="github_fix_pr")

    result = await db_session.execute(select(Execution).where(Execution.tool_name == "failure_prediction_model"))
    records = result.scalars().all()

    assert len(records) >= 1
    assert all(record.tool_name == "failure_prediction_model" for record in records)


@pytest.mark.asyncio
async def test_executions_filter_by_status(db_session: AsyncSession):
    await _seed_execution(db_session, tool_name="status_tool", status="completed")
    await _seed_execution(db_session, tool_name="status_tool", status="failed")
    await _seed_execution(db_session, tool_name="status_tool", status="completed")

    result = await db_session.execute(select(Execution).where(Execution.status == "completed"))
    records = result.scalars().all()

    assert len(records) >= 1
    assert all(record.status == "completed" for record in records)


@pytest.mark.asyncio
async def test_executions_filter_by_days(db_session: AsyncSession):
    now = datetime.now(tz=timezone.utc)
    await _seed_execution(
        db_session,
        tool_name="date_tool",
        summary="Old execution",
        started_at=now - timedelta(days=10),
    )
    await _seed_execution(db_session, tool_name="date_tool", summary="New execution", started_at=now)

    cutoff = now - timedelta(days=3)
    result = await db_session.execute(select(Execution).where(Execution.started_at >= cutoff))
    records = result.scalars().all()

    assert any(record.summary == "New execution" for record in records)
    assert all(record.summary != "Old execution" for record in records)


@pytest.mark.asyncio
async def test_audit_endpoint_filters_by_tool_and_success_alias(db_session: AsyncSession):
    await _seed_execution(db_session, tool_name="github_log_downloader", status="completed")
    await _seed_execution(db_session, tool_name="failure_prediction_model", status="failed")

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/audit?limit=50&tool=github&status=success",
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["tool_name"] == "github_log_downloader"
    assert body[0]["status"] == "completed"
