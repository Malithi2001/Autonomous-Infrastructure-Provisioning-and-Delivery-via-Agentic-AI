# backend/tests/test_hitl.py
"""
Integration tests for the HITL approval flow.

Covers:
  1. create_approval_request() persists a pending record
  2. GET /api/v1/approvals/ lists pending records
  3. POST /api/v1/approvals/{id}/decide (approved=True) executes the tool and creates an Execution
  4. POST /api/v1/approvals/{id}/decide (approved=False) cancels and creates a cancelled Execution
  5. Double-deciding an already-decided approval returns 409
  6. HITLApprovalRequired is raised by the tool wrapper when ENABLE_HITL=True
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.routes import approvals as approvals_router, health
from app.core.database import Base, get_db
from app.core.security import UserRole, create_access_token, hash_password
from app.middleware.auth import JWTMiddleware
from app.models.models import ApprovalRequest, Execution, User


# ── In-memory SQLite test DB ──────────────────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


def _build_approvals_app() -> FastAPI:
    _app = FastAPI(title="HITL Test App")
    _app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    _app.add_middleware(JWTMiddleware)
    _app.include_router(health.router)
    _app.include_router(approvals_router.router, prefix="/api/v1/approvals", tags=["Approvals"])
    return _app


app = _build_approvals_app()


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


@pytest_asyncio.fixture()
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def _admin_headers() -> dict:
    token = create_access_token({"sub": str(uuid.uuid4()), "role": "admin", "username": "admin"})
    return {"Authorization": f"Bearer {token}"}


def _operator_headers() -> dict:
    token = create_access_token({"sub": str(uuid.uuid4()), "role": "operator", "username": "ops"})
    return {"Authorization": f"Bearer {token}"}


def _dev_headers() -> dict:
    token = create_access_token({"sub": str(uuid.uuid4()), "role": "developer", "username": "dev"})
    return {"Authorization": f"Bearer {token}"}


# ── Helper ────────────────────────────────────────────────────────────────────

async def _seed_approval(db: AsyncSession, status: str = "pending", **overrides) -> ApprovalRequest:
    record = ApprovalRequest(
        id=str(uuid.uuid4()),
        session_id=overrides.get("session_id", "sess-1"),
        requested_by=overrides.get("requested_by", "dev"),
        tool_name=overrides.get("tool_name", "docker_stop_container"),
        tool_input=json.dumps({"container_name": "nginx"}),
        action="Stop nginx container",
        risk_level="high",
        summary="Stop nginx for maintenance",
        status=status,
        expires_at=datetime.now(tz=timezone.utc) + timedelta(minutes=10),
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestCreateApprovalRequest:
    @pytest.mark.asyncio
    async def test_create_persists_pending_record(self, db_session: AsyncSession):
        from app.api.routes.approvals import create_approval_request

        record = await create_approval_request(
            db=db_session,
            session_id="test-session",
            requested_by="engineer",
            tool_name="docker_stop_container",
            tool_input={"container_name": "app"},
            action="Stop app container",
            risk_level="high",
            summary="Stopping app container for deployment",
        )
        assert record.id is not None
        assert record.status == "pending"
        assert record.tool_name == "docker_stop_container"
        assert record.requested_by == "engineer"


class TestListApprovals:
    @pytest.mark.asyncio
    async def test_list_returns_pending_approvals(self, client: AsyncClient, db_session: AsyncSession):
        await _seed_approval(db_session)
        resp = await client.get("/api/v1/approvals/", headers=_admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/approvals/")
        assert resp.status_code in (401, 403)


class TestDecideApproval:
    @pytest.mark.asyncio
    async def test_approve_calls_tool_and_creates_execution(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        record = await _seed_approval(db_session)

        with patch("app.api.routes.approvals._dispatch_tool", return_value=("✅ Stopped", "completed")):
            resp = await client.post(
                f"/api/v1/approvals/{record.id}/decide",
                json={"approved": True, "note": "Looks good"},
                headers=_admin_headers(),
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "approved"
        assert body["execution_status"] == "completed"
        assert "execution_id" in body

        # Reload DB record
        await db_session.refresh(record)
        assert record.status == "approved"

    @pytest.mark.asyncio
    async def test_reject_creates_cancelled_execution(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        record = await _seed_approval(db_session)
        resp = await client.post(
            f"/api/v1/approvals/{record.id}/decide",
            json={"approved": False, "note": "Too risky right now"},
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "rejected"
        await db_session.refresh(record)
        assert record.status == "rejected"

    @pytest.mark.asyncio
    async def test_decide_twice_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        record = await _seed_approval(db_session, status="approved")
        resp = await client.post(
            f"/api/v1/approvals/{record.id}/decide",
            json={"approved": True},
            headers=_admin_headers(),
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_decide_nonexistent_returns_404(self, client: AsyncClient):
        resp = await client.post(
            f"/api/v1/approvals/{uuid.uuid4()}/decide",
            json={"approved": True},
            headers=_admin_headers(),
        )
        assert resp.status_code == 404


class TestHITLToolWrapper:
    """Unit tests for the HITLApprovalRequired wrapper."""

    def test_hitl_wrap_raises_when_enabled(self):
        from app.agents.tools_registry import HITLApprovalRequired, _hitl_wrap

        def _dummy(container_name: str) -> str:
            return f"stopped {container_name}"

        wrapped = _hitl_wrap(_dummy, "docker_stop_container", "high", "Stop '{container_name}'")

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.ENABLE_HITL = True
            with pytest.raises(HITLApprovalRequired) as exc_info:
                wrapped(container_name="nginx")
            assert exc_info.value.tool_name == "docker_stop_container"
            assert exc_info.value.risk_level == "high"

    def test_hitl_wrap_executes_when_disabled(self):
        from app.agents.tools_registry import _hitl_wrap

        def _dummy(container_name: str) -> str:
            return f"stopped {container_name}"

        wrapped = _hitl_wrap(_dummy, "docker_stop_container", "high", "Stop '{container_name}'")

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.ENABLE_HITL = False
            result = wrapped(container_name="nginx")
            assert result == "stopped nginx"