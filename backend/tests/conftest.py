"""
Pytest fixtures — async SQLite in-memory DB + minimal FastAPI test app.

We build a stripped-down app (no LangChain/agent routes) so the test suite
doesn't require heavyweight dependencies that are irrelevant to auth testing.
"""
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import UserRole, create_access_token, hash_password
from app.models.models import User  # registers all models on Base.metadata

# ── In-memory SQLite engine ───────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


# ── Build a minimal FastAPI app with only auth + health routes ────────────────
def _build_test_app() -> FastAPI:
    from app.api.routes import auth, health
    from app.middleware.auth import JWTMiddleware

    _app = FastAPI(title="Test App")
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    _app.add_middleware(JWTMiddleware)
    _app.include_router(health.router, tags=["Health"])
    _app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    return _app


app = _build_test_app()


# ── Schema: create once per session, drop at the end ─────────────────────────
@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── Per-test DB session ───────────────────────────────────────────────────────
@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(autouse=True)
async def override_db(db_session: AsyncSession):
    """Wire the test DB session into FastAPI dependency injection."""
    async def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.pop(get_db, None)


# ── HTTP client ───────────────────────────────────────────────────────────────
@pytest_asyncio.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ── Seed users ────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture()
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        email="admin@example.com",
        username="admin",
        hashed_password=hash_password("adminpass1"),
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def engineer_user(db_session: AsyncSession) -> User:
    user = User(
        email="engineer@example.com",
        username="engineer",
        hashed_password=hash_password("engineerpass1"),
        role=UserRole.ENGINEER,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def viewer_user(db_session: AsyncSession) -> User:
    user = User(
        email="viewer@example.com",
        username="viewer",
        hashed_password=hash_password("viewerpass1"),
        role=UserRole.VIEWER,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


# ── Token helpers ─────────────────────────────────────────────────────────────
@pytest.fixture()
def admin_token(admin_user: User) -> str:
    return create_access_token({
        "sub": str(admin_user.id),
        "role": admin_user.role.value,
        "username": admin_user.username,
    })


@pytest.fixture()
def engineer_token(engineer_user: User) -> str:
    return create_access_token({
        "sub": str(engineer_user.id),
        "role": engineer_user.role.value,
        "username": engineer_user.username,
    })


@pytest.fixture()
def viewer_token(viewer_user: User) -> str:
    return create_access_token({
        "sub": str(viewer_user.id),
        "role": viewer_user.role.value,
        "username": viewer_user.username,
    })
