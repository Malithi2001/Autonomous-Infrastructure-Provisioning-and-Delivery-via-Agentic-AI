"""Pydantic request/response schemas."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ── Auth Schemas ──────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    role: str


# ── Agent / Chat Schemas ──────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="Natural language DevOps command")
    session_id: Optional[str] = Field(None, description="Conversation session ID. Omit to start a new session.")


class IntermediateStep(BaseModel):
    tool: str
    tool_input: Any
    output: str


class ChatResponse(BaseModel):
    output: str
    session_id: str
    intermediate_steps: list[IntermediateStep] = []
    execution_id: Optional[str] = None
    requires_approval: bool = False
    approval_id: Optional[str] = None


# ── Execution Schemas ─────────────────────────────────────────────────────────

class ExecutionOut(BaseModel):
    id: UUID
    session_id: str
    command: str
    status: str
    risk_level: str
    tool_used: Optional[str]
    result: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── HITL Approval Schemas ─────────────────────────────────────────────────────

class ApprovalRequestOut(BaseModel):
    id: UUID
    execution_id: UUID
    description: str
    status: str
    expires_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class ApprovalDecision(BaseModel):
    approved: bool
    note: Optional[str] = Field(None, max_length=500)
