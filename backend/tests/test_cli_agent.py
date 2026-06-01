"""Unit tests for the specialized CLI Agent."""
from __future__ import annotations

from app.agents.agent_types import AgentTask
from app.agents.cli_agent import CLIAgent


def test_cli_agent_lists_containers(monkeypatch):
    monkeypatch.setattr(
        "app.agents.cli_agent.docker_tool.list_containers",
        lambda: "- [running] api (image: demo-api, ports: 8000->8000/tcp)",
    )

    result = CLIAgent().handle(AgentTask(message="show running containers"))

    assert result.selected_agent == "cli_agent"
    assert result.intent == "docker_list_containers"
    assert result.risk_level == "low"
    assert result.success is True
    assert "api" in result.result
    assert result.metadata["tool_called"] == "list_containers"


def test_cli_agent_supports_docker_ps_intent(monkeypatch):
    monkeypatch.setattr(
        "app.agents.cli_agent.docker_tool.list_containers",
        lambda: "No containers found.",
    )

    result = CLIAgent().handle(AgentTask(message="docker ps"))

    assert result.success is True
    assert result.intent == "docker_list_containers"
    assert result.result == "No containers found."


def test_cli_agent_reads_container_logs_from_context(monkeypatch):
    captured = {}

    def _fake_logs(container_name: str) -> str:
        captured["container_name"] = container_name
        return "2026-05-31 api started"

    monkeypatch.setattr("app.agents.cli_agent.docker_tool.get_container_logs", _fake_logs)

    result = CLIAgent().handle(
        AgentTask(
            message="show container logs",
            context={"container_name": "api"},
        )
    )

    assert result.success is True
    assert result.intent == "docker_get_container_logs"
    assert result.result == "2026-05-31 api started"
    assert result.metadata["tool_called"] == "get_container_logs"
    assert result.metadata["container_name"] == "api"
    assert captured["container_name"] == "api"


def test_cli_agent_container_logs_requires_container_name():
    result = CLIAgent().handle(AgentTask(message="docker logs"))

    assert result.success is False
    assert result.intent == "docker_get_container_logs"
    assert "container_name" in result.result
    assert result.metadata["tool_called"] == "get_container_logs"


def test_cli_agent_handles_tool_errors(monkeypatch):
    def _raise_error() -> str:
        raise RuntimeError("Docker socket unavailable")

    monkeypatch.setattr("app.agents.cli_agent.docker_tool.list_containers", _raise_error)

    result = CLIAgent().handle(AgentTask(message="list containers"))

    assert result.success is False
    assert result.intent == "docker_list_containers"
    assert "Docker socket unavailable" in result.result
    assert result.metadata["tool_called"] == "list_containers"


def test_cli_agent_returns_unsupported_intent():
    result = CLIAgent().handle(AgentTask(message="delete all files"))

    assert result.success is False
    assert result.intent == "unsupported_cli_intent"
    assert result.metadata == {}
