"""Security utilities: JWT, password hashing, RBAC."""
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── RBAC Roles ────────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    VIEWER = "viewer"           # Read-only: view logs, metrics
    DEVELOPER = "developer"     # Can trigger deployments in non-prod
    OPERATOR = "operator"       # Full DevOps access, no prod deployments
    ADMIN = "admin"             # Full access including production


# Permission matrix per role
ROLE_PERMISSIONS: dict[UserRole, list[str]] = {
    UserRole.VIEWER: ["logs:read", "metrics:read", "executions:read"],
    UserRole.DEVELOPER: [
        "logs:read", "metrics:read", "executions:read",
        "agent:chat", "deployments:staging",
    ],
    UserRole.OPERATOR: [
        "logs:read", "logs:write", "metrics:read", "executions:read",
        "agent:chat", "deployments:staging", "deployments:production",
        "infrastructure:read", "infrastructure:write",
    ],
    UserRole.ADMIN: ["*"],  # Wildcard: all permissions
}


def has_permission(role: UserRole, permission: str) -> bool:
    """Check if a role has the given permission."""
    perms = ROLE_PERMISSIONS.get(role, [])
    return "*" in perms or permission in perms


# ── Password Utilities ────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT Utilities ─────────────────────────────────────────────────────────────

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


def require_permission(permission: str):
    """FastAPI dependency: ensures current user has the required permission."""
    async def _check(token: str = Depends(oauth2_scheme)):
        payload = decode_token(token)
        role = UserRole(payload.get("role", UserRole.VIEWER))
        if not has_permission(role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required.",
            )
        return payload
    return _check


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Return the decoded JWT payload for the current caller."""
    return decode_token(token)
