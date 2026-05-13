"""Authentication and user-management endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    ACCESS_TOKEN_COOKIE_NAME,
    PUBLIC_SIGNUP_ROLES,
    UserRole,
    coerce_role,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    require_permission,
    role_profile,
    verify_password,
)
from app.models.models import User, UserSession
from app.schemas.schemas import (
    AdminCreateUser,
    LoginResponse,
    RefreshRequest,
    RolesResponse,
    TokenResponse,
    UserOut,
    UserRegister,
)

router = APIRouter()


def _cookie_secure() -> bool:
    if settings.ENVIRONMENT.strip().lower() in {"production", "prod", "release"}:
        return True
    return bool(settings.COOKIE_SECURE)


def _cookie_samesite() -> Literal["lax", "strict", "none"]:
    value = settings.COOKIE_SAMESITE.strip().lower()
    if value in {"lax", "strict", "none"}:
        return cast(Literal["lax", "strict", "none"], value)
    return "lax"


def _set_access_cookie(response: Response, access_token: str) -> None:
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
        secure=_cookie_secure(),
        httponly=True,
        samesite=_cookie_samesite(),
    )


def _clear_access_cookie(response: Response) -> None:
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        path="/",
        secure=_cookie_secure(),
        httponly=True,
        samesite=_cookie_samesite(),
    )


async def _read_login_payload(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Invalid login payload.")
        return payload

    form = await request.form()
    return {
        "email": form.get("email"),
        "username": form.get("username"),
        "password": form.get("password"),
    }


def _token_payload(user: User) -> dict[str, str]:
    return {"sub": str(user.id), "role": user.role.value, "username": user.username}


def _login_response(user: User, access_token: str, refresh_token: str) -> LoginResponse:
    return LoginResponse(
        user=UserOut.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=str(user.id),
        username=user.username,
        role=user.role.value,
    )


async def _ensure_unique_user(db: AsyncSession, email: str, username: str) -> None:
    result = await db.execute(select(User).where(or_(User.email == email, User.username == username)))
    existing = result.scalar_one_or_none()
    if existing:
        if existing.email == email:
            raise HTTPException(status_code=400, detail="Email already registered.")
        raise HTTPException(status_code=400, detail="Username already taken.")


async def _create_user_record(
    db: AsyncSession,
    *,
    email: str,
    username: str,
    password: str,
    role: UserRole,
    is_active: bool = True,
) -> User:
    await _ensure_unique_user(db, email, username)
    user = User(
        email=email,
        username=username,
        hashed_password=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _create_session_and_cookie(
    user: User,
    request: Request,
    response: Response,
    db: AsyncSession,
) -> tuple[str, str]:
    access_token = create_access_token(data=_token_payload(user))
    refresh_token = create_refresh_token(data=_token_payload(user))
    refresh_payload = decode_token(refresh_token)

    db.add(
        UserSession(
            user_id=str(user.id),
            refresh_token=refresh_token,
            expires_at=datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc),
            is_revoked=False,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    )
    await db.flush()
    _set_access_cookie(response, access_token)
    return access_token, refresh_token


@router.get("/roles", response_model=RolesResponse)
async def get_roles():
    """Return role profiles for the login/signup UI."""
    ordered = [UserRole.ADMIN, UserRole.OPERATOR, UserRole.DEVELOPER, UserRole.VIEWER]
    return {
        "roles": [role_profile(role) for role in ordered],
        "public_signup_roles": [role.value for role in sorted(PUBLIC_SIGNUP_ROLES, key=lambda role: role.value)],
    }


@router.post("/register", response_model=LoginResponse, status_code=201)
async def register(payload: UserRegister, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    """
    Public self-signup.

    Only viewer/developer accounts can be created publicly. Operator and admin
    accounts are privileged and must be provisioned from an existing admin account.
    """
    requested_role = coerce_role(payload.role or UserRole.DEVELOPER)
    if requested_role not in PUBLIC_SIGNUP_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin and operator accounts must be created by an existing admin.",
        )

    user = await _create_user_record(
        db,
        email=str(payload.email),
        username=payload.username,
        password=payload.password,
        role=requested_role,
        is_active=True,
    )
    access_token, refresh_token = await _create_session_and_cookie(user, request, response, db)
    return _login_response(user, access_token, refresh_token)


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    """Login with email/password or legacy username/password and set an httpOnly JWT cookie."""
    payload = await _read_login_payload(request)
    identifier = (payload.get("email") or payload.get("username") or "").strip()
    password = payload.get("password") or ""

    if not identifier or not password:
        raise HTTPException(status_code=422, detail="Email/username and password are required.")

    result = await db.execute(select(User).where(or_(User.email == identifier, User.username == identifier)))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated.")

    access_token, refresh_token = await _create_session_and_cookie(user, request, response, db)
    return _login_response(user, access_token, refresh_token)


@router.post("/logout", status_code=204)
async def logout(response: Response):
    _clear_access_cookie(response)
    return None


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshRequest, response: Response, db: AsyncSession = Depends(get_db)):
    token_data = decode_token(payload.refresh_token)
    if token_data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token.")

    result = await db.execute(
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(UserSession.refresh_token == payload.refresh_token)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=401, detail="Refresh session not found.")

    session, user = row
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if session.is_revoked or expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked.")

    session.is_revoked = True

    access_token = create_access_token(data=_token_payload(user))
    refresh_token = create_refresh_token(data=_token_payload(user))
    refresh_payload = decode_token(refresh_token)

    db.add(
        UserSession(
            user_id=str(user.id),
            refresh_token=refresh_token,
            expires_at=datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc),
            is_revoked=False,
        )
    )
    await db.flush()
    _set_access_cookie(response, access_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=str(user.id),
        username=user.username,
        role=user.role.value,
    )


@router.get("/me", response_model=UserOut)
async def get_current_user_info(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, current_user["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.get("/users", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("users:manage")),
):
    """Admin-only user directory."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(
    payload: AdminCreateUser,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("users:manage")),
):
    """Admin-only user provisioning for admin/operator/developer/viewer accounts."""
    role = coerce_role(payload.role)
    user = await _create_user_record(
        db,
        email=str(payload.email),
        username=payload.username,
        password=payload.password,
        role=role,
        is_active=payload.is_active,
    )
    return user
