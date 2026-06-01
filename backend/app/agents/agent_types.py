"""Shared data contracts for the multi-agent orchestration layer."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentTask(BaseModel):
    """Input passed from the orchestration agent to specialized agents."""

    message: str
    user_id: str | None = None
    session_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    """Structured response returned by specialized agents."""

    selected_agent: str
    intent: str
    risk_level: str
    success: bool
    result: str
    metadata: dict[str, Any] = Field(default_factory=dict)
