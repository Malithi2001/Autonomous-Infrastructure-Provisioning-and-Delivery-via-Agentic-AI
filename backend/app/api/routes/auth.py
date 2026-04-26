"""Authentication endpoints — register, login, refresh, logout, /me."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    UserRole,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user_payload,
    hash_password,
    verify_password,
)
from app.models.models import User, UserSession
from app.schemas.schemas import (
    RefreshRequest,
    TokenResponse,
    UserOut,
    UserRegister,
)

router = APIRouter()


# ── Register ──────────────────────────────────────────────────────────────────

@router.post("/register", status_code=201, summary="Register a new user account")
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    """
    Create a new user.  Role defaults to *developer* unless specified.

    - **email**: must be unique
    - **username**: 3–50 chars, must be unique
    - **password**: minimum 8 characters
    """
    # Check for duplicate email
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered.")

    # Check for duplicate username
    result = await db.execute(select(User).where(User.username == payload.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken.")

    role = UserRole(payload.role) if payload.role else UserRole.DEVELOPER

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role=role,
    )
    db.add(user)
    await db.flush()
    await db.commit()
    await db.refresh(user)

    return {
        "message": "User registered successfully.",
        "user_id": str(user.id),
        "username": user.username,
        "role": user.role.value,
    }


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse, summary="Login and receive JWT tokens")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate with **username** + **password** (form-encoded).

    Returns an **access token** (short-lived) and a **refresh token**
    (long-lived, stored in ``user_sessions``).
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Login attempt for username: {form_data.username}")
    
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"User {form_data.username} not found in database")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    password_valid = verify_password(form_data.password, user.hashed_password)
    logger.info(f"User {form_data.username} found. Password valid: {password_valid}")
    
    if not password_valid:
        logger.warning(f"Invalid password for user {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated.")

    token_data = {
        "sub": str(user.id),
        "role": user.role.value,
        "username": user.username,
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Persist the refresh token as a session record
    refresh_payload = decode_token(refresh_token, expected_type="refresh")
    expires_at = datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc)

    session = UserSession(
        user_id=user.id,
        refresh_token=refresh_token,
        expires_at=expires_at,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(session)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=str(user.id),
        username=user.username,
        role=user.role.value,
    )


# ── Refresh ───────────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse, summary="Exchange refresh token for new tokens")
async def refresh_tokens(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    **Token rotation**: validate the supplied refresh token, revoke it, and
    issue a brand-new access + refresh token pair.
    """
    try:
        payload = decode_token(body.refresh_token, expected_type="refresh")
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    # Verify token exists in DB and is not revoked
    result = await db.execute(
        select(UserSession).where(UserSession.refresh_token == body.refresh_token)
    )
    session: Optional[UserSession] = result.scalar_one_or_none()

    if session is None or session.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked or is unknown.",
        )

    if session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired.",
        )

    # Fetch the user
    result = await db.execute(select(User).where(User.id == session.user_id))
    user: Optional[User] = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=403, detail="User not found or deactivated.")

    # Revoke old session (token rotation)
    session.is_revoked = True

    # Issue new tokens
    token_data = {
        "sub": str(user.id),
        "role": user.role.value,
        "username": user.username,
    }
    new_access = create_access_token(token_data)
    new_refresh = create_refresh_token(token_data)

    new_refresh_payload = decode_token(new_refresh, expected_type="refresh")
    new_expires_at = datetime.fromtimestamp(new_refresh_payload["exp"], tz=timezone.utc)

    new_session = UserSession(
        user_id=user.id,
        refresh_token=new_refresh,
        expires_at=new_expires_at,
    )
    db.add(new_session)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        user_id=str(user.id),
        username=user.username,
        role=user.role.value,
    )


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout", status_code=200, summary="Revoke the current refresh token")
async def logout(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    _payload: dict = Depends(get_current_user_payload),
):
    """Revoke the provided refresh token, invalidating this session."""
    result = await db.execute(
        select(UserSession).where(UserSession.refresh_token == body.refresh_token)
    )
    session: Optional[UserSession] = result.scalar_one_or_none()
    if session:
        session.is_revoked = True
    return {"message": "Logged out successfully."}


# ── /me ───────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserOut, summary="Get current user profile")
async def get_me(
    payload: dict = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_db),
):
    """Return profile information for the authenticated user."""
    user_id = payload["sub"]
    result = await db.execute(select(User).where(User.id == user_id))
    user: Optional[User] = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user
