"""
Session memory factory.

Selects the best available backend in order:
  1. Redis (recommended for production / multi-worker)
  2. PostgreSQL via SQLChatMessageHistory
  3. In-process ConversationBufferWindowMemory (fallback — dev only)

Set MEMORY_BACKEND=redis|postgres|inmemory in your .env to override detection.
"""
from __future__ import annotations

from app.core.config import settings
from app.core.logging import logger


def _make_redis_memory(session_id: str):
    from langchain_community.chat_message_histories import RedisChatMessageHistory
    from langchain.memory import ConversationBufferWindowMemory

    history = RedisChatMessageHistory(
        session_id=session_id,
        url=settings.REDIS_URL,
        ttl=86400 * 7,           # 7-day TTL — matches refresh token lifetime
        key_prefix="agent_memory:",
    )
    return ConversationBufferWindowMemory(
        chat_memory=history,
        memory_key="chat_history",
        return_messages=True,
        k=20,
        input_key="input",
        output_key="output",
    )


def _make_postgres_memory(session_id: str):
    from langchain_community.chat_message_histories import SQLChatMessageHistory
    from langchain.memory import ConversationBufferWindowMemory

    # Use the sync connection string (SQLChatMessageHistory uses SQLAlchemy sync)
    sync_url = settings.DATABASE_URL
    if sync_url.startswith("postgresql+asyncpg://"):
        sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    elif sync_url.startswith("sqlite+aiosqlite://"):
        sync_url = sync_url.replace("sqlite+aiosqlite://", "sqlite://", 1)

    history = SQLChatMessageHistory(
        session_id=session_id,
        connection_string=sync_url,
        table_name="agent_chat_history",
    )
    return ConversationBufferWindowMemory(
        chat_memory=history,
        memory_key="chat_history",
        return_messages=True,
        k=20,
        input_key="input",
        output_key="output",
    )


def _make_inmemory_memory():
    from langchain.memory import ConversationBufferWindowMemory
    return ConversationBufferWindowMemory(
        memory_key="chat_history",
        return_messages=True,
        k=20,
        input_key="input",
        output_key="output",
    )


def build_memory(session_id: str):
    """
    Return the best available memory backend for ``session_id``.

    Detection order: explicit env var → Redis (if REDIS_URL set) → Postgres → in-memory.
    """
    backend = getattr(settings, "MEMORY_BACKEND", "auto").lower()

    if backend == "redis" or (backend == "auto" and settings.REDIS_URL):
        try:
            mem = _make_redis_memory(session_id)
            logger.info("agent.memory.backend", backend="redis", session_id=session_id)
            return mem
        except Exception as exc:
            logger.warning("agent.memory.redis_failed", error=str(exc))

    if backend == "postgres" or (backend == "auto" and settings.DATABASE_URL):
        try:
            mem = _make_postgres_memory(session_id)
            logger.info("agent.memory.backend", backend="postgres", session_id=session_id)
            return mem
        except Exception as exc:
            logger.warning("agent.memory.postgres_failed", error=str(exc))

    logger.warning("agent.memory.backend", backend="inmemory", session_id=session_id)
    return _make_inmemory_memory()
