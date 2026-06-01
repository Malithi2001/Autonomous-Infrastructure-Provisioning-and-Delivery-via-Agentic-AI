"""Specialized CLI Agent for safe Docker and command-adjacent operations."""
from __future__ import annotations

from app.agents.agent_types import AgentResult, AgentTask
from app.tools import docker_tool


class CLIAgent:
    """Handle low-risk CLI-style requests by delegating to existing tools."""

    name = "cli_agent"

    def handle(self, task: AgentTask) -> AgentResult:
        """Process a CLI-related task and return a structured agent result."""
        message = task.message.lower().strip()

        if self._is_container_list_intent(message):
            return self._list_containers()

        if self._is_container_logs_intent(message):
            return self._get_container_logs(task)

        return AgentResult(
            selected_agent=self.name,
            intent="unsupported_cli_intent",
            risk_level="low",
            success=False,
            result="CLI Agent could not match this request to a supported safe Docker operation.",
            metadata={},
        )

    def _list_containers(self) -> AgentResult:
        tool_name = "list_containers"
        try:
            result = docker_tool.list_containers()
            return AgentResult(
                selected_agent=self.name,
                intent="docker_list_containers",
                risk_level="low",
                success=True,
                result=result,
                metadata={"tool_called": tool_name},
            )
        except Exception as exc:
            return AgentResult(
                selected_agent=self.name,
                intent="docker_list_containers",
                risk_level="low",
                success=False,
                result=f"Unable to list Docker containers: {exc}",
                metadata={"tool_called": tool_name},
            )

    def _get_container_logs(self, task: AgentTask) -> AgentResult:
        tool_name = "get_container_logs"
        container_name = str(task.context.get("container_name") or "").strip()
        if not container_name:
            return AgentResult(
                selected_agent=self.name,
                intent="docker_get_container_logs",
                risk_level="low",
                success=False,
                result="Container name is required in task.context['container_name'] to read container logs.",
                metadata={"tool_called": tool_name},
            )

        try:
            result = docker_tool.get_container_logs(container_name)
            return AgentResult(
                selected_agent=self.name,
                intent="docker_get_container_logs",
                risk_level="low",
                success=True,
                result=result,
                metadata={"tool_called": tool_name, "container_name": container_name},
            )
        except Exception as exc:
            return AgentResult(
                selected_agent=self.name,
                intent="docker_get_container_logs",
                risk_level="low",
                success=False,
                result=f"Unable to read Docker logs for container '{container_name}': {exc}",
                metadata={"tool_called": tool_name, "container_name": container_name},
            )

    @staticmethod
    def _is_container_list_intent(message: str) -> bool:
        supported_phrases = (
            "show running containers",
            "docker ps",
            "list containers",
            "show containers",
        )
        return any(phrase in message for phrase in supported_phrases)

    @staticmethod
    def _is_container_logs_intent(message: str) -> bool:
        return "docker logs" in message or "container logs" in message
