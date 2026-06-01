"""Database connection and session management."""
from __future__ import annotations

import ssl
from typing import Any, AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import or_, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.logging import logger


def _normalize_database_url(database_url: str) -> str:
    value = database_url.strip()
    if value.startswith("postgresql+asyncpg://"):
        async_url = value
    elif value.startswith("postgresql://"):
        async_url = value.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif value.startswith("postgres://"):
        async_url = value.replace("postgres://", "postgresql+asyncpg://", 1)
    else:
        async_url = value

    if "pooler.supabase.com" in async_url:
        parts = urlsplit(async_url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query.setdefault("prepared_statement_cache_size", "0")
        async_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))

    return async_url


def _connect_args(async_url: str) -> dict[str, Any]:
    if async_url.startswith("sqlite"):
        return {"timeout": 30}
    if async_url.startswith("postgresql+asyncpg"):
        args: dict[str, Any] = {"command_timeout": 60}
        if "supabase.com" in async_url:
            if settings.DATABASE_SSL_VERIFY:
                args["ssl"] = ssl.create_default_context()
            else:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                args["ssl"] = ssl_context
        if "pooler.supabase.com" in async_url:
            args["statement_cache_size"] = 0
        return args
    return {}


async_url = _normalize_database_url(settings.DATABASE_URL)
connect_args = _connect_args(async_url)

engine = create_async_engine(
    async_url,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    connect_args=connect_args,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

try:
    logger.info("database.configured", database_url=make_url(async_url).render_as_string(hide_password=True))
except Exception:
    logger.info("database.configured")


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


async def init_db() -> None:
    """Initialize database tables on startup."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await ensure_schema_compatibility(conn)
        await ensure_default_admin()
    except Exception as exc:
        logger.warning("database.init.skipped", error=str(exc))


async def ensure_schema_compatibility(conn) -> None:
    """
    Apply small additive schema fixes for demo databases created before newer
    ORM fields existed. Base.metadata.create_all() does not alter existing
    tables, so nullable columns added during MVP development need this shim.
    """
    dialect = conn.dialect.name
    if dialect == "postgresql":
        await conn.execute(
            text(
                "ALTER TABLE workflow_failures "
                "ADD COLUMN IF NOT EXISTS recommendation_json TEXT"
            )
        )
        return

    if dialect == "sqlite":
        result = await conn.execute(text("PRAGMA table_info(workflow_failures)"))
        columns = {row[1] for row in result.fetchall()}
        if "recommendation_json" not in columns:
            await conn.execute(
                text("ALTER TABLE workflow_failures ADD COLUMN recommendation_json TEXT")
            )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency: yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def ensure_default_admin() -> None:
    """Seed safe demo RBAC accounts for local/development environments."""
    from app.core.security import UserRole, hash_password
    from app.models.models import User

    demo_users = [
        {
            "email": settings.DEFAULT_ADMIN_EMAIL,
            "username": settings.DEFAULT_ADMIN_USERNAME,
            "password": settings.DEFAULT_ADMIN_PASSWORD,
            "role": UserRole.ADMIN,
        },
        {
            "email": "operator@devops.example.com",
            "legacy_email": "operator@devops.local",
            "username": "operator",
            "password": "operator123",
            "role": UserRole.OPERATOR,
        },
        {
            "email": "devops.engineer@example.com",
            "username": "devops.engineer",
            "password": "developer123",
            "role": UserRole.DEVELOPER,
        },
        {
            "email": "viewer@company.example.com",
            "legacy_email": "viewer@company.local",
            "username": "viewer",
            "password": "viewer123",
            "role": UserRole.VIEWER,
        },
    ]

    if settings.ENVIRONMENT.strip().lower() in {"production", "prod", "release"}:
        demo_users = demo_users[:1]

    async with AsyncSessionLocal() as session:
        created = []
        updated = []
        for demo in demo_users:
            legacy_email = demo.get("legacy_email")
            lookup_conditions = [
                User.username == demo["username"],
                User.email == demo["email"],
            ]
            if legacy_email:
                lookup_conditions.append(User.email == legacy_email)

            result = await session.execute(
                select(User).where(or_(*lookup_conditions))
            )
            user = result.scalar_one_or_none()
            if user:
                if legacy_email and user.email == legacy_email:
                    user.email = demo["email"]
                    updated.append(demo["username"])
                continue

            session.add(
                User(
                    email=demo["email"],
                    username=demo["username"],
                    hashed_password=hash_password(demo["password"]),
                    role=demo["role"],
                    is_active=True,
                )
            )
            created.append(demo["username"])

        if created or updated:
            await session.commit()
            logger.info("database.default_users.seeded", usernames=created, updated_usernames=updated)
