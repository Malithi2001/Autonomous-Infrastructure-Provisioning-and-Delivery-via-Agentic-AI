"""Security utilities: JWT, password hashing, RBAC decorators."""
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import wraps
from typing import Callable, Optional

from fastapi import Depends, HTTPException, Request, status
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
    ENGINEER = "engineer"       # Alias used in RBAC decorator; maps to OPERATOR
    OPERATOR = "operator"       # Full DevOps access, no prod deployments
    ADMIN = "admin"             # Full access including production


# Role hierarchy — higher index = more privilege
_ROLE_HIERARCHY: list[UserRole] = [
    UserRole.VIEWER,
    UserRole.DEVELOPER,
    UserRole.ENGINEER,
    UserRole.OPERATOR,
    UserRole.ADMIN,
]

# Permission matrix per role
ROLE_PERMISSIONS: dict[UserRole, list[str]] = {
    UserRole.VIEWER:    ["logs:read", "metrics:read", "executions:read"],
    UserRole.DEVELOPER: [
        "logs:read", "metrics:read", "executions:read",
        "agent:chat", "deployments:staging",
    ],
    UserRole.ENGINEER: [
        "logs:read", "metrics:read", "executions:read",
        "agent:chat", "deployments:staging", "deployments:production",
        "infrastructure:read",
    ],
    UserRole.OPERATOR: [
        "logs:read", "logs:write", "metrics:read", "executions:read",
        "agent:chat", "deployments:staging", "deployments:production",
        "infrastructure:read", "infrastructure:write",
    ],
    UserRole.ADMIN: ["*"],  # Wildcard — all permissions
}


def has_permission(role: UserRole, permission: str) -> bool:
    """Return True if *role* carries *permission* (or the wildcard)."""
    perms = ROLE_PERMISSIONS.get(role, [])
    return "*" in perms or permission in perms


def role_rank(role: UserRole) -> int:
    """Return the numeric rank of a role (higher = more privileged)."""
    try:
        return _ROLE_HIERARCHY.index(role)
    except ValueError:
        return -1


def role_satisfies(user_role: UserRole, required_role: UserRole) -> bool:
    """Return True if *user_role* is equal to or above *required_role*."""
    return role_rank(user_role) >= role_rank(required_role)


# ── Password Utilities ────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT Utilities ─────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a short-lived access token (default: ACCESS_TOKEN_EXPIRE_MINUTES)."""
    import uuid as _uuid
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access", "jti": str(_uuid.uuid4())})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a long-lived refresh token (default: REFRESH_TOKEN_EXPIRE_DAYS days)."""
    import uuid as _uuid
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh", "jti": str(_uuid.uuid4())})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> dict:
    """Decode and validate a JWT; raises 401 on any failure."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise credentials_exc

    if payload.get("type") != expected_type:
        raise credentials_exc

    if payload.get("sub") is None:
        raise credentials_exc

    return payload


# ── FastAPI Dependencies ──────────────────────────────────────────────────────

async def get_current_user_payload(token: str = Depends(oauth2_scheme)) -> dict:
    """Dependency: decode the bearer token and return its payload."""
    return decode_token(token, expected_type="access")


def require_permission(permission: str):
    """Dependency factory: gate a route on a named permission string."""
    async def _check(payload: dict = Depends(get_current_user_payload)):
        role_str = payload.get("role", UserRole.VIEWER.value)
        try:
            role = UserRole(role_str)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Unknown role in token.")
        if not has_permission(role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required.",
            )
        return payload
    return _check


# ── RBAC Decorator ────────────────────────────────────────────────────────────

def require_role(*roles: str):
    """
    Route decorator that enforces role-based access control.

    Usage::

        @router.get("/admin-only")
        @require_role("admin")
        async def admin_route(request: Request):
            ...

    The decorator inspects ``request.state.user_payload`` which is populated
    by the ``jwt_middleware`` in ``app/middleware/auth.py``.  If you prefer
    pure FastAPI dependency injection, use the ``require_permission`` factory
    instead.

    Accepted role strings (case-insensitive): admin, operator, engineer,
    developer, viewer.  Hierarchy is respected — e.g. ``require_role('viewer')``
    passes for all roles.
    """
    required = [UserRole(r.lower()) for r in roles]

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Pull request from kwargs or positional args
            request: Optional[Request] = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="require_role decorator requires 'request: Request' parameter.",
                )

            payload: Optional[dict] = getattr(request.state, "user_payload", None)
            if payload is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            role_str = payload.get("role", UserRole.VIEWER.value)
            try:
                user_role = UserRole(role_str)
            except ValueError:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail="Unknown role in token.")

            # Pass if the user's role satisfies ANY of the required roles
            if not any(role_satisfies(user_role, req) for req in required):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"One of roles {[r.value for r in required]} required; "
                           f"you have '{user_role.value}'.",
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator
