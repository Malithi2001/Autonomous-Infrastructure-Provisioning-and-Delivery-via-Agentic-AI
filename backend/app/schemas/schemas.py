import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.security import UserRole


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = Field(None, max_length=128)


class ChatResponse(BaseModel):
    output: str
    session_id: str
    intermediate_steps: List[str] = Field(default_factory=list)
    # Set when the agent queues a HITL approval instead of executing directly
    pending_approval_id: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    role: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    role: Optional[UserRole] = None


class ApprovalDecision(BaseModel):
    approved: bool
    note: Optional[str] = None


class ApprovalRequestOut(BaseModel):
    id: str
    session_id: str
    requested_by: str
    tool_name: str
    action: str
    risk_level: str
    summary: str
    status: str
    decided_by: Optional[str] = None
    decision_note: Optional[str] = None
    decided_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ExecutionOut(BaseModel):
    id: str
    session_id: str
    requested_by: str
    tool_name: str
    status: str
    summary: str
    details: Optional[str] = None
    source: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    approval_id: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)