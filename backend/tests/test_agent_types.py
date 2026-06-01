"""Unit tests for shared multi-agent Pydantic models."""
from __future__ import annotations

from app.agents.agent_types import AgentResult, AgentTask


def test_agent_task_defaults_context_to_independent_dicts():
    first = AgentTask(message="show running containers")
    second = AgentTask(message="diagnose failure")

    first.context["container_name"] = "api"

    assert first.message == "show running containers"
    assert first.user_id is None
    assert first.session_id is None
    assert first.context == {"container_name": "api"}
    assert second.context == {}


def test_agent_result_defaults_metadata_to_independent_dicts():
    first = AgentResult(
        selected_agent="cli_agent",
        intent="docker_list_containers",
        risk_level="low",
        success=True,
        result="No containers found.",
    )
    second = AgentResult(
        selected_agent="orchestration_agent",
        intent="unknown",
        risk_level="low",
        success=False,
        result="I could not route this request to a specialized agent.",
    )

    first.metadata["tool_called"] = "list_containers"

    assert first.metadata == {"tool_called": "list_containers"}
    assert second.metadata == {}
