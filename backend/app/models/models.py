"""
SQLAlchemy ORM models.

Tables
------
users            — auth accounts
user_sessions    — refresh token store
chat_messages    — persistent conversation memory (per session_id)
approval_requests — HITL pending/decided gates
executions       — full audit trail of every agent action
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey,
    Integer, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.security import UserRole


# ── Users & Sessions ──────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()), unique=True, nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=lambda obj: [e.value for e in obj], native_enum=False),
        nullable=False, default=UserRole.DEVELOPER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession", back_populates="user",
        cascade="all, delete-orphan", lazy="selectin",
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()), unique=True, nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    refresh_token: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    user: Mapped[User] = relationship("User", back_populates="sessions")


# ── Persistent Chat Memory ────────────────────────────────────────────────────

class ChatMessage(Base):
    """
    One row per message turn.  role ∈ {'human', 'ai'}.
    Loaded by RedisChatMessageHistory / SQLChatMessageHistory substitute.
    """
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(10), nullable=False)   # 'human' | 'ai'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )


# ── HITL Approval Requests ────────────────────────────────────────────────────

class ApprovalRequest(Base):
    """
    Created by the agent when it classifies an action as HIGH or CRITICAL risk.
    The agent suspends execution until an operator/admin decides.
    """
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()), nullable=False,
    )
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    # Who triggered the action
    requested_by: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tool_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Human-readable description of the planned action
    action: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)   # low|medium|high|critical
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    # pending | approved | rejected | expired
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)

    # Serialised agent state / tool call payload — resumed on approval
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Decision metadata
    decided_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    execution: Mapped["Execution | None"] = relationship(
        "Execution", back_populates="approval", uselist=False,
    )


# ── Execution Audit Trail ─────────────────────────────────────────────────────

class Execution(Base):
    """
    Written for every agent action (approved or low-risk direct).
    Provides full audit trail including intermediate reasoning steps.
    """
    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()), nullable=False,
    )
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    requested_by: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tool_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    # pending | running | completed | failed | cancelled
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)   # JSON intermediate steps
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 'agent' | 'webhook' | …

    # FK to approval if the action required one
    approval_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("approval_requests.id", ondelete="SET NULL"), nullable=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    approval: Mapped["ApprovalRequest | None"] = relationship(
        "ApprovalRequest", back_populates="execution",
    )
