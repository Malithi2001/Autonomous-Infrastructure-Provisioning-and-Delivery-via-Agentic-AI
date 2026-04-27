import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.security import UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
        unique=True, nullable=False,
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
        "UserSession", back_populates="user", cascade="all, delete-orphan", lazy="selectin",
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
        unique=True, nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    refresh_token: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    user: Mapped[User] = relationship("User", back_populates="sessions")


class ApprovalRequest(Base):
    """
    Persists a pending HIGH/CRITICAL action that requires a human decision
    before the agent is allowed to execute it.

    Lifecycle:  pending → approved | rejected | timed_out
    """
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
        unique=True, nullable=False,
    )
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    requested_by: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_input: Mapped[str] = mapped_column(Text, nullable=False)           # JSON
    action: Mapped[str] = mapped_column(String(255), nullable=False)        # human-readable label
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)     # low|medium|high|critical
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    decided_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    decision_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    executions: Mapped[list["Execution"]] = relationship(
        "Execution", back_populates="approval", cascade="all, delete-orphan",
    )


class Execution(Base):
    """
    Audit trail for every action actually run by the agent (approved or low-risk).
    """
    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
        unique=True, nullable=False,
    )
    approval_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("approval_requests.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    requested_by: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_input: Mapped[str] = mapped_column(Text, nullable=False)   # JSON
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running", index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # agent|manual|webhook
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    approval: Mapped[Optional["ApprovalRequest"]] = relationship(
        "ApprovalRequest", back_populates="executions",
    )