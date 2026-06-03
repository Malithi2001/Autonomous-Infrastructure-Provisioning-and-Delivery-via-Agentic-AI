"""Security utilities: JWT, password hashing, and role-based access control."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional
import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
ACCESS_TOKEN_COOKIE_NAME = settings.COOKIE_NAME or "devops_access_token"

DESKTOP_USER_ID = "desktop_user"
DESKTOP_USER_EMAIL = "desktop@local.app"
DESKTOP_USER_USERNAME = "desktop_user"


class UserRole(str, Enum):
    VIEWER = "viewer"
    DEVELOPER = "developer"
    OPERATOR = "operator"
    ADMIN = "admin"


ROLE_LABELS: dict[UserRole, str] = {
    UserRole.ADMIN: "Admin",
    UserRole.OPERATOR: "Operator",
    UserRole.DEVELOPER: "Developer",
    UserRole.VIEWER: "Viewer",
}

ROLE_DESCRIPTIONS: dict[UserRole, str] = {
    UserRole.ADMIN: (
        "Full platform owner. Can manage users, audit activity, approve changes, and use all agent tools."
    ),
    UserRole.OPERATOR: (
        "Operations controller. Can use production-safe operational tools and decide approval gates."
    ),
    UserRole.DEVELOPER: (
        "Builder workflow. Can chat with the agent, inspect systems, and use lower-risk development/staging tools."
    ),
    UserRole.VIEWER: (
        "Read-only observer. Can ask the agent for safe insight without operational or approval access."
    ),
}

# Public self-signup is intentionally limited. Privileged accounts must be
# created by an admin so users cannot self-grant operational access.
PUBLIC_SIGNUP_ROLES: set[UserRole] = {UserRole.DEVELOPER, UserRole.VIEWER}

ROLE_PERMISSIONS: dict[UserRole, list[str]] = {
    UserRole.VIEWER: [
        "agent:chat",
        "approvals:read",
        "executions:read",
    ],
    UserRole.DEVELOPER: [
        "agent:chat",
        "agents:orchestrate",
        "cicd:read",
        "cicd:generate",
        "failures:predict",
        "repositories:read",
        "workflow_failures:read",
        "executions:read",
        "logs:read",
        "deployments:staging",
    ],
    UserRole.OPERATOR: [
        "agent:chat",
        "agents:orchestrate",
        "cicd:read",
        "cicd:generate",
        "failures:predict",
        "repositories:read",
        "repositories:write",
        "workflow_failures:read",
        "workflow_failures:write",
        "audit:read",
        "logs:read",
        "logs:write",
        "metrics:read",
        "executions:read",
        "executions:write",
        "approvals:read",
        "approvals:decide",
        "deployments:staging",
        "deployments:production",
        "infrastructure:read",
        "infrastructure:write",
    ],
    UserRole.ADMIN: ["*"],
}


def coerce_role(value: str | UserRole | None) -> UserRole:
    """Return a safe UserRole, defaulting to viewer for unknown values."""
    if isinstance(value, UserRole):
        return value
    try:
        return UserRole(str(value or UserRole.VIEWER.value).lower())
    except ValueError:
        return UserRole.VIEWER


def get_role_permissions(role: str | UserRole | None) -> list[str]:
    role_value = coerce_role(role)
    permissions = ROLE_PERMISSIONS.get(role_value, [])
    if "*" in permissions:
        return ["*"]
    return sorted(set(permissions))


def has_permission(role: str | UserRole | None, permission: str) -> bool:
    perms = ROLE_PERMISSIONS.get(coerce_role(role), [])
    return "*" in perms or permission in perms


def role_profile(role: str | UserRole | None) -> dict:
    role_value = coerce_role(role)
    return {
        "role": role_value.value,
        "label": ROLE_LABELS[role_value],
        "description": ROLE_DESCRIPTIONS[role_value],
        "permissions": get_role_permissions(role_value),
        "can_self_signup": role_value in PUBLIC_SIGNUP_ROLES,
    }


def auth_bypass_enabled() -> bool:
    """Return true when local desktop mode disables JWT and RBAC checks."""
    return settings.auth_disabled


def desktop_user_payload() -> dict:
    """Synthetic admin user used only for local desktop mode."""
    return {
        "sub": DESKTOP_USER_ID,
        "id": DESKTOP_USER_ID,
        "username": DESKTOP_USER_USERNAME,
        "email": DESKTOP_USER_EMAIL,
        "role": UserRole.ADMIN.value,
        "is_desktop_user": True,
    }


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = _build_token_payload(
        data,
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = _build_token_payload(
        data,
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _build_token_payload(data: dict, expires_delta: timedelta, token_type: str) -> dict:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "type": token_type, "jti": str(uuid.uuid4())})
    return to_encode


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _get_request_token(request: Request, bearer_token: str | None = None) -> str:
    token = bearer_token or request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


def _decode_access_payload(request: Request, bearer_token: str | None = None) -> dict:
    raw_token = _get_request_token(request, bearer_token)
    payload = decode_token(raw_token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type.")
    payload["role"] = coerce_role(payload.get("role")).value
    return payload


def require_permission(permission: str):
    """FastAPI dependency: require a specific permission from bearer token or httpOnly cookie."""

    async def _check(request: Request, token: str | None = Depends(oauth2_scheme)):
        if auth_bypass_enabled():
            return desktop_user_payload()
        payload = _decode_access_payload(request, token)
        role = coerce_role(payload.get("role"))
        if not has_permission(role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required for this action.",
            )
        return payload

    return _check


def require_role(*roles: UserRole):
    allowed = {role.value for role in roles}

    async def _check(request: Request, token: str | None = Depends(oauth2_scheme)):
        if auth_bypass_enabled():
            return desktop_user_payload()
        payload = _decode_access_payload(request, token)
        if payload.get("role") not in allowed and payload.get("role") != UserRole.ADMIN.value:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role.")
        return payload

    return _check


async def get_current_user(request: Request, token: str | None = Depends(oauth2_scheme)) -> dict:
    """Return decoded JWT payload from Authorization bearer or secure httpOnly cookie."""
    if auth_bypass_enabled():
        return desktop_user_payload()
    return _decode_access_payload(request, token)
