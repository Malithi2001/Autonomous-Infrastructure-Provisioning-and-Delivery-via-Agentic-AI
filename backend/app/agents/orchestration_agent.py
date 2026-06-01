"""Deterministic orchestration agent for routing user requests."""
from __future__ import annotations

from typing import Protocol

from app.agents.agent_types import AgentResult, AgentTask
from app.agents.cicd_agent import CICDAgent
from app.agents.cli_agent import CLIAgent
from app.agents.diagnosis_agent import DiagnosisAgent
from app.agents.github_agent import GitHubAgent


class _SpecializedAgent(Protocol):
    def handle(self, task: AgentTask) -> AgentResult:
        """Handle an agent task."""


class _ApprovalPlanningAgent(_SpecializedAgent, Protocol):
    def approval_plan(self, task: AgentTask) -> dict | None:
        """Return approval plan for gated actions."""


class OrchestrationAgent:
    """Route user tasks to the correct specialized agent."""

    name = "orchestration_agent"

    def __init__(
        self,
        cli_agent: _SpecializedAgent | None = None,
        cicd_agent: _SpecializedAgent | None = None,
        diagnosis_agent: _SpecializedAgent | None = None,
        github_agent: _SpecializedAgent | None = None,
    ) -> None:
        self.cli_agent = cli_agent or CLIAgent()
        self.cicd_agent = cicd_agent or CICDAgent()
        self.diagnosis_agent = diagnosis_agent or DiagnosisAgent()
        self.github_agent = github_agent or GitHubAgent()

    def approval_plan(self, task: AgentTask) -> dict | None:
        """Return a pending-approval plan for medium/high-risk actions."""
        message = task.message.lower().strip()
        if self._is_github_request(message) and hasattr(self.github_agent, "approval_plan"):
            return self.github_agent.approval_plan(task)  # type: ignore[attr-defined]
        return None

    def handle(self, task: AgentTask) -> AgentResult:
        """Route a task to one specialized agent using deterministic rules."""
        message = task.message.lower().strip()

        if self._is_cli_request(message):
            return self.cli_agent.handle(task)
        if self._is_cicd_request(message):
            return self.cicd_agent.handle(task)
        if self._is_diagnosis_request(message):
            return self.diagnosis_agent.handle(task)
        if self._is_github_request(message):
            return self.github_agent.handle(task)

        return AgentResult(
            selected_agent=self.name,
            intent="unknown",
            risk_level="low",
            success=False,
            result="I could not route this request to a specialized agent.",
            metadata={},
        )

    @staticmethod
    def _is_cli_request(message: str) -> bool:
        routing_terms = (
            "docker",
            "container",
            "running containers",
        )
        return any(term in message for term in routing_terms)

    @staticmethod
    def _is_cicd_request(message: str) -> bool:
        routing_terms = (
            "generate workflow",
            "ci pipeline",
            "github actions yaml",
            "detect stack",
            "generate ci workflow",
            "generate github actions workflow",
        )
        return any(term in message for term in routing_terms)

    @staticmethod
    def _is_diagnosis_request(message: str) -> bool:
        routing_terms = (
            "analyze log",
            "diagnose failure",
            "why did ci fail",
            "error log",
            "failed workflow",
        )
        return any(term in message for term in routing_terms)

    @staticmethod
    def _is_github_request(message: str) -> bool:
        routing_terms = (
            "github",
            "repository",
            "pull request",
            "workflow pr",
            "fix pr",
            "scan repo",
            "trigger workflow",
        )
        return any(term in message for term in routing_terms)
