"""Pydantic request/response schemas."""
import uuid
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.security import UserRole


class IntermediateStep(BaseModel):
    tool: str
    input: Any = ""
    output: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = Field(None, max_length=128)


class ChatResponse(BaseModel):
    output: str
    session_id: str
    intermediate_steps: List[IntermediateStep] = Field(default_factory=list)
    requires_approval: Optional[bool] = None
    approval_id: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20)


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    role: str


class LoginResponse(TokenResponse):
    user: UserOut


class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    role: Optional[UserRole] = UserRole.DEVELOPER


class AdminCreateUser(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.DEVELOPER
    is_active: bool = True


class RoleProfile(BaseModel):
    role: UserRole
    label: str
    description: str
    permissions: list[str]
    can_self_signup: bool = False


class RolesResponse(BaseModel):
    roles: list[RoleProfile]
    public_signup_roles: list[UserRole]


class ApprovalDecision(BaseModel):
    approved: bool
    note: Optional[str] = None


class ApprovalRequestOut(BaseModel):
    id: uuid.UUID
    requested_by: str
    action: str
    risk_level: str
    summary: str
    status: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    decided_by: Optional[str] = None
    decision_note: Optional[str] = None
    decided_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ExecutionOut(BaseModel):
    id: uuid.UUID
    requested_by: str
    status: str
    summary: str
    details: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    source: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
