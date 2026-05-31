"""Tests for GitHub App service helpers."""
from __future__ import annotations

import hashlib
import hmac
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.services import github_app_service


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict, headers: dict[str, str] | None = None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = ""
        self.reason = "OK"

    def json(self):
        return self._payload


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


def test_create_app_jwt_uses_app_id_and_private_key(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(github_app_service.settings, "GITHUB_APP_ID", "12345")
    monkeypatch.setattr(
        github_app_service.settings,
        "GITHUB_APP_PRIVATE_KEY",
        "-----BEGIN PRIVATE KEY-----\\nabc\\n-----END PRIVATE KEY-----",
    )

    def _fake_encode(payload, key, algorithm):
        captured["payload"] = payload
        captured["key"] = key
        captured["algorithm"] = algorithm
        return "signed-app-jwt"

    monkeypatch.setattr(github_app_service.jwt, "encode", _fake_encode)

    token = github_app_service.create_app_jwt()

    assert token == "signed-app-jwt"
    assert captured["payload"]["iss"] == "12345"
    assert captured["payload"]["exp"] > captured["payload"]["iat"]
    assert captured["key"] == "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----"
    assert captured["algorithm"] == "RS256"


def test_verify_webhook_signature_prefers_github_app_secret(monkeypatch):
    payload = b'{"zen":"Keep it logically tidy."}'
    secret = "app-webhook-secret"
    signature = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    monkeypatch.setattr(github_app_service.settings, "GITHUB_APP_WEBHOOK_SECRET", secret)
    monkeypatch.setattr(github_app_service.settings, "GITHUB_WEBHOOK_SECRET", "legacy-secret")

    assert github_app_service.verify_webhook_signature(payload, signature) is True
    assert github_app_service.verify_webhook_signature(payload, "sha256=bad") is False


def test_get_installation_access_token(monkeypatch):
    monkeypatch.setattr(github_app_service, "create_app_jwt", lambda: "app-jwt")

    def _fake_post(url, headers, timeout):
        assert url.endswith("/app/installations/99/access_tokens")
        assert headers["Authorization"] == "Bearer app-jwt"
        assert timeout == github_app_service.REQUEST_TIMEOUT_SECONDS
        return _FakeResponse(201, {"token": "installation-token"})

    monkeypatch.setattr(github_app_service.requests, "post", _fake_post)

    assert github_app_service.get_installation_access_token(99) == "installation-token"


def test_get_installation_repositories(monkeypatch):
    monkeypatch.setattr(github_app_service, "get_installation_access_token", lambda installation_id: "install-token")

    def _fake_get(url, headers, params, timeout):
        assert url.endswith("/installation/repositories")
        assert headers["Authorization"] == "Bearer install-token"
        assert params["page"] == 1
        return _FakeResponse(
            200,
            {
                "repositories": [
                    {"full_name": "octo-org/demo-app", "default_branch": "main"},
                    {"full_name": "octo-org/api", "default_branch": "develop"},
                ]
            },
        )

    monkeypatch.setattr(github_app_service.requests, "get", _fake_get)

    repositories = github_app_service.get_installation_repositories(99)

    assert [repo["full_name"] for repo in repositories] == ["octo-org/demo-app", "octo-org/api"]


@pytest.mark.asyncio
async def test_upsert_and_list_repository_installations(db_session: AsyncSession):
    repo = await github_app_service.upsert_repository_installation(
        db_session,
        installation_id=123,
        repository={"full_name": "octo-org/demo-app", "default_branch": "main"},
    )

    assert uuid.UUID(repo.id)
    assert repo.installation_id == 123
    assert repo.repo_full_name == "octo-org/demo-app"
    assert repo.owner == "octo-org"
    assert repo.repo == "demo-app"
    assert repo.status == "active"

    updated = await github_app_service.upsert_repository_installation(
        db_session,
        installation_id=456,
        repository={"full_name": "octo-org/demo-app", "default_branch": "develop"},
    )
    records = await github_app_service.list_installed_repositories(db_session)

    assert updated.id == repo.id
    assert updated.installation_id == 456
    assert updated.default_branch == "develop"
    assert len(records) == 1
