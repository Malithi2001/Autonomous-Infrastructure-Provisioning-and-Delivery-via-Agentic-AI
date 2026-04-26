"""
Comprehensive pytest test suite for JWT auth + RBAC.

Coverage:
  - POST /api/v1/auth/register
  - POST /api/v1/auth/login
  - POST /api/v1/auth/refresh
  - POST /api/v1/auth/logout
  - GET  /api/v1/auth/me
  - Token validation / middleware
  - @require_role RBAC decorator
  - RBAC via require_permission dependency
"""
import time
from datetime import timedelta

import pytest
from httpx import AsyncClient

from app.core.security import (
    UserRole,
    create_access_token,
    create_refresh_token,
    decode_token,
    has_permission,
    role_satisfies,
)
from app.models.models import User


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Unit tests — security utility functions
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurityUtils:
    """Pure-function unit tests — no DB or HTTP involved."""

    # ── password ──────────────────────────────────────────────────────────────
    def test_hash_and_verify_password(self):
        from app.core.security import hash_password, verify_password
        hashed = hash_password("secret99")
        assert verify_password("secret99", hashed)
        assert not verify_password("badpass99", hashed)

    # ── JWT round-trip ─────────────────────────────────────────────────────────
    def test_create_and_decode_access_token(self):
        token = create_access_token({"sub": "abc", "role": "admin", "username": "u"})
        payload = decode_token(token, expected_type="access")
        assert payload["sub"] == "abc"
        assert payload["role"] == "admin"

    def test_create_and_decode_refresh_token(self):
        token = create_refresh_token({"sub": "xyz", "role": "viewer", "username": "v"})
        payload = decode_token(token, expected_type="refresh")
        assert payload["sub"] == "xyz"
        assert payload["type"] == "refresh"

    def test_decode_wrong_token_type_raises(self):
        from fastapi import HTTPException
        access = create_access_token({"sub": "u", "role": "admin", "username": "u"})
        with pytest.raises(HTTPException) as exc:
            decode_token(access, expected_type="refresh")  # wrong type
        assert exc.value.status_code == 401

    def test_expired_token_raises(self):
        from fastapi import HTTPException
        token = create_access_token(
            {"sub": "u", "role": "admin", "username": "u"},
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(HTTPException) as exc:
            decode_token(token)
        assert exc.value.status_code == 401

    def test_tampered_token_raises(self):
        from fastapi import HTTPException
        token = create_access_token({"sub": "u", "role": "admin", "username": "u"})
        tampered = token[:-4] + "XXXX"
        with pytest.raises(HTTPException):
            decode_token(tampered)

    # ── RBAC logic ─────────────────────────────────────────────────────────────
    def test_has_permission_admin_wildcard(self):
        assert has_permission(UserRole.ADMIN, "any:permission")

    def test_has_permission_viewer_limited(self):
        assert has_permission(UserRole.VIEWER, "logs:read")
        assert not has_permission(UserRole.VIEWER, "agent:chat")

    def test_has_permission_engineer(self):
        assert has_permission(UserRole.ENGINEER, "deployments:production")
        assert not has_permission(UserRole.ENGINEER, "infrastructure:write")

    def test_role_satisfies_hierarchy(self):
        # Admin satisfies everything
        assert role_satisfies(UserRole.ADMIN, UserRole.VIEWER)
        assert role_satisfies(UserRole.ADMIN, UserRole.ADMIN)
        # Viewer does NOT satisfy engineer
        assert not role_satisfies(UserRole.VIEWER, UserRole.ENGINEER)
        # Engineer satisfies developer
        assert role_satisfies(UserRole.ENGINEER, UserRole.DEVELOPER)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. POST /api/v1/auth/register
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestRegister:

    async def test_register_success(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "new@example.com",
            "username": "newuser",
            "password": "strongpass1",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "newuser"
        assert "user_id" in data

    async def test_register_default_role_is_developer(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "dev@example.com",
            "username": "devuser",
            "password": "strongpass1",
        })
        assert resp.status_code == 201
        assert resp.json()["role"] == "developer"

    async def test_register_duplicate_email_fails(self, client: AsyncClient):
        payload = {"email": "dup@example.com", "username": "dup1", "password": "strongpass1"}
        await client.post("/api/v1/auth/register", json=payload)
        payload2 = {"email": "dup@example.com", "username": "dup2", "password": "strongpass1"}
        resp = await client.post("/api/v1/auth/register", json=payload2)
        assert resp.status_code == 400
        assert "email" in resp.json()["detail"].lower()

    async def test_register_duplicate_username_fails(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json={
            "email": "u1@example.com", "username": "sameuser", "password": "strongpass1"
        })
        resp = await client.post("/api/v1/auth/register", json={
            "email": "u2@example.com", "username": "sameuser", "password": "strongpass1"
        })
        assert resp.status_code == 400
        assert "username" in resp.json()["detail"].lower()

    async def test_register_short_password_fails(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "short@example.com",
            "username": "shortpw",
            "password": "abc",           # < 8 chars
        })
        assert resp.status_code == 422   # Pydantic validation error

    async def test_register_invalid_email_fails(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "username": "bademail",
            "password": "strongpass1",
        })
        assert resp.status_code == 422

    async def test_register_short_username_fails(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "ok@example.com",
            "username": "ab",            # < 3 chars
            "password": "strongpass1",
        })
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# 3. POST /api/v1/auth/login
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestLogin:

    async def _register(self, client, suffix=""):
        await client.post("/api/v1/auth/register", json={
            "email": f"login{suffix}@example.com",
            "username": f"loginuser{suffix}",
            "password": "loginpass1",
        })

    async def test_login_success_returns_tokens(self, client: AsyncClient):
        await self._register(client, "a")
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "loginusera", "password": "loginpass1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] in {r.value for r in UserRole}

    async def test_login_wrong_password_fails(self, client: AsyncClient):
        await self._register(client, "b")
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "loginuserb", "password": "wrongpass"},
        )
        assert resp.status_code == 401

    async def test_login_nonexistent_user_fails(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "nobody", "password": "nopass"},
        )
        assert resp.status_code == 401

    async def test_login_access_token_is_decodable(self, client: AsyncClient):
        await self._register(client, "c")
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "loginuserc", "password": "loginpass1"},
        )
        token = resp.json()["access_token"]
        payload = decode_token(token, expected_type="access")
        assert payload["username"] == "loginuserc"

    async def test_login_inactive_user_forbidden(
        self, client: AsyncClient, db_session
    ):
        from sqlalchemy import select
        await self._register(client, "d")
        # Deactivate the user directly in the DB
        from sqlalchemy import update
        from app.models.models import User as UserModel
        await db_session.execute(
            update(UserModel).where(UserModel.username == "loginuserd").values(is_active=False)
        )
        await db_session.flush()

        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "loginuserd", "password": "loginpass1"},
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# 4. POST /api/v1/auth/refresh
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestRefreshToken:

    async def _login(self, client, suffix=""):
        un = f"refreshuser{suffix}"
        await client.post("/api/v1/auth/register", json={
            "email": f"refresh{suffix}@example.com",
            "username": un,
            "password": "refreshpass1",
        })
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": un, "password": "refreshpass1"},
        )
        return resp.json()

    async def test_refresh_returns_new_tokens(self, client: AsyncClient):
        tokens = await self._login(client, "a")
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert resp.status_code == 200
        new_tokens = resp.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        # Tokens must be rotated (different from originals)
        assert new_tokens["access_token"] != tokens["access_token"]
        assert new_tokens["refresh_token"] != tokens["refresh_token"]

    async def test_refresh_old_token_revoked(self, client: AsyncClient):
        tokens = await self._login(client, "b")
        old_refresh = tokens["refresh_token"]
        # Use the refresh token once
        await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
        # Reusing the old token should fail
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
        assert resp.status_code == 401

    async def test_refresh_invalid_token_fails(self, client: AsyncClient):
        # No login needed — we test a garbage token
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "totally.invalid.token"},
        )
        assert resp.status_code == 401

    async def test_refresh_access_token_as_refresh_fails(self, client: AsyncClient):
        tokens = await self._login(client, "c")
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["access_token"]},  # wrong type
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# 5. GET /api/v1/auth/me + middleware
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestGetMe:

    async def test_me_with_valid_token(
        self, client: AsyncClient, admin_user: User, admin_token: str
    ):
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"

    async def test_me_without_token_returns_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_me_with_invalid_token_returns_401(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer garbage.token.here"},
        )
        assert resp.status_code == 401

    async def test_me_with_expired_token_returns_401(self, client: AsyncClient, admin_user):
        expired = create_access_token(
            {"sub": str(admin_user.id), "role": "admin", "username": "admin"},
            expires_delta=timedelta(seconds=-1),
        )
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired}"},
        )
        assert resp.status_code == 401

    async def test_me_with_refresh_token_returns_401(self, client: AsyncClient, admin_user):
        """Refresh tokens must not be accepted on access-token endpoints."""
        refresh = create_refresh_token(
            {"sub": str(admin_user.id), "role": "admin", "username": "admin"}
        )
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {refresh}"},
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# 6. POST /api/v1/auth/logout
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestLogout:

    async def _login(self, client, suffix=""):
        un = f"logoutuser{suffix}"
        await client.post("/api/v1/auth/register", json={
            "email": f"logout{suffix}@example.com",
            "username": un,
            "password": "logoutpass1",
        })
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": un, "password": "logoutpass1"},
        )
        return resp.json()

    async def test_logout_success(self, client: AsyncClient):
        tokens = await self._login(client, "a")
        resp = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 200
        assert "logged out" in resp.json()["message"].lower()

    async def test_refresh_after_logout_fails(self, client: AsyncClient):
        tokens = await self._login(client, "b")
        # Logout
        await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        # Refresh should now fail
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# 7. JWT Middleware
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestJWTMiddleware:

    async def test_public_path_no_token_needed(self, client: AsyncClient):
        """Health endpoint must be accessible without a token."""
        resp = await client.get("/health")
        assert resp.status_code == 200

    async def test_protected_path_requires_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_malformed_auth_header_returns_401(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "NotBearer token"},
        )
        assert resp.status_code == 401

    async def test_valid_token_passes_middleware(
        self, client: AsyncClient, admin_user: User, admin_token: str
    ):
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 8. RBAC — @require_role decorator (via an inline test route)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestRequireRoleDecorator:
    """
    We register ephemeral test routes on the FastAPI app to exercise the
    @require_role decorator in isolation without touching production routes.
    """

    @pytest.fixture(autouse=True)
    def _register_test_routes(self):
        from fastapi import Request
        from fastapi.routing import APIRouter
        from app.core.security import require_role
        import tests.conftest as _conftest
        _app = _conftest.app

        router = APIRouter(prefix="/test-rbac")

        @router.get("/admin-only")
        @require_role("admin")
        async def admin_only(request: Request):
            return {"ok": True, "role": "admin"}

        @router.get("/engineer-plus")
        @require_role("engineer")
        async def engineer_plus(request: Request):
            return {"ok": True}

        @router.get("/viewer-plus")
        @require_role("viewer")
        async def viewer_plus(request: Request):
            return {"ok": True}

        _app.include_router(router)
        yield
        _app.routes[:] = [r for r in _app.routes if not getattr(r, "path", "").startswith("/test-rbac")]

    async def test_admin_can_access_admin_route(
        self, client: AsyncClient, admin_user: User, admin_token: str
    ):
        resp = await client.get(
            "/test-rbac/admin-only",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

    async def test_viewer_cannot_access_admin_route(
        self, client: AsyncClient, viewer_user: User, viewer_token: str
    ):
        resp = await client.get(
            "/test-rbac/admin-only",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    async def test_engineer_can_access_engineer_route(
        self, client: AsyncClient, engineer_user: User, engineer_token: str
    ):
        resp = await client.get(
            "/test-rbac/engineer-plus",
            headers={"Authorization": f"Bearer {engineer_token}"},
        )
        assert resp.status_code == 200

    async def test_admin_satisfies_engineer_route(
        self, client: AsyncClient, admin_user: User, admin_token: str
    ):
        """Admin is above engineer in hierarchy — should be granted access."""
        resp = await client.get(
            "/test-rbac/engineer-plus",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

    async def test_viewer_cannot_access_engineer_route(
        self, client: AsyncClient, viewer_user: User, viewer_token: str
    ):
        resp = await client.get(
            "/test-rbac/engineer-plus",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    async def test_all_roles_can_access_viewer_route(
        self,
        client: AsyncClient,
        admin_user, admin_token,
        engineer_user, engineer_token,
        viewer_user, viewer_token,
    ):
        for token in (admin_token, engineer_token, viewer_token):
            resp = await client.get(
                "/test-rbac/viewer-plus",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200

    async def test_no_token_returns_401_on_rbac_route(self, client: AsyncClient):
        resp = await client.get("/test-rbac/admin-only")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# 9. RBAC — require_permission dependency
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestRequirePermissionDependency:
    """Test the require_permission FastAPI dependency factory."""

    @pytest.fixture(autouse=True)
    def _register_perm_routes(self):
        from fastapi import Depends, Request
        from fastapi.routing import APIRouter
        from app.core.security import require_permission
        import tests.conftest as _conftest
        _app = _conftest.app

        router = APIRouter(prefix="/test-perm")

        @router.get("/infra-write")
        async def infra_write(payload=Depends(require_permission("infrastructure:write"))):
            return {"ok": True, "user": payload["username"]}

        @router.get("/logs-read")
        async def logs_read(payload=Depends(require_permission("logs:read"))):
            return {"ok": True}

        _app.include_router(router)
        yield
        _app.routes[:] = [r for r in _app.routes if not getattr(r, "path", "").startswith("/test-perm")]

    async def test_operator_can_write_infra(
        self, client: AsyncClient, db_session, admin_user
    ):
        # Create an operator user
        from app.core.security import hash_password
        op = User(
            email="op@example.com",
            username="opuser",
            hashed_password=hash_password("oppass1"),
            role=UserRole.OPERATOR,
        )
        db_session.add(op)
        await db_session.flush()
        await db_session.refresh(op)
        token = create_access_token({"sub": str(op.id), "role": "operator", "username": "opuser"})

        resp = await client.get(
            "/test-perm/infra-write",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    async def test_viewer_cannot_write_infra(
        self, client: AsyncClient, viewer_user, viewer_token
    ):
        resp = await client.get(
            "/test-perm/infra-write",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    async def test_viewer_can_read_logs(
        self, client: AsyncClient, viewer_user, viewer_token
    ):
        resp = await client.get(
            "/test-perm/logs-read",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 200

    async def test_admin_has_all_permissions(
        self, client: AsyncClient, admin_user, admin_token
    ):
        resp = await client.get(
            "/test-perm/infra-write",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
