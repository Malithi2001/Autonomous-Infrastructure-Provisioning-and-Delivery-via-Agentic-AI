"""Authentication endpoints — register, login, refresh."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
    UserRole,
)
from app.models.models import User, UserSession
from app.schemas.schemas import RefreshRequest, TokenResponse, UserOut, UserRegister

router = APIRouter()


@router.post("/register", status_code=201)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered.")

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role=payload.role or UserRole.DEVELOPER,
    )
    db.add(user)
    await db.flush()
    return {"message": "User registered successfully.", "user_id": str(user.id)}


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login and receive a JWT access token."""
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated.")

    token_payload = {"sub": str(user.id), "role": user.role.value, "username": user.username}
    access_token = create_access_token(data=token_payload)
    refresh_token = create_refresh_token(data=token_payload)
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

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=str(user.id),
        username=user.username,
        role=user.role.value,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh token for a new access token pair."""
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
    if session.is_revoked or session.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked.")

    session.is_revoked = True

    token_payload = {"sub": str(user.id), "role": user.role.value, "username": user.username}
    access_token = create_access_token(data=token_payload)
    refresh_token = create_refresh_token(data=token_payload)
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

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=str(user.id),
        username=user.username,
        role=user.role.value,
    )


@router.get("/me", response_model=UserOut)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's profile."""
    user = await db.get(User, current_user["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user
