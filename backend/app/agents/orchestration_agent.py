"""Deterministic orchestration agent for routing user requests."""
from __future__ import annotations

import re
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
        prepared_task = self._prepare_task(task)
        route = self._route(prepared_task)
        if route == "github" and hasattr(self.github_agent, "approval_plan"):
            return self.github_agent.approval_plan(prepared_task)  # type: ignore[attr-defined]
        return None

    def handle(self, task: AgentTask) -> AgentResult:
        """Route a task to one specialized agent using deterministic rules."""
        prepared_task = self.prepare_task(task)
        route = self.route_task(prepared_task)

        if route == "cli":
            return self.cli_agent.handle(prepared_task)
        if route == "cicd":
            return self.cicd_agent.handle(prepared_task)
        if route == "diagnosis":
            return self.diagnosis_agent.handle(prepared_task)
        if route == "github":
            return self.github_agent.handle(prepared_task)

        return AgentResult(
            selected_agent=self.name,
            intent="unknown",
            risk_level="low",
            success=False,
            result="I could not route this request to a specialized agent.",
            metadata={},
        )

    def prepare_task(self, task: AgentTask) -> AgentTask:
        """Return a task enriched with deterministic context extracted from the message."""
        return self._prepare_task(task)

    def route_task(self, task: AgentTask) -> str:
        """Return the specialized-agent route for an already prepared task."""
        return self._route(task)

    def _prepare_task(self, task: AgentTask) -> AgentTask:
        extracted = self._extract_context(task.message)
        merged_context = {**extracted, **task.context}
        if task.context.get("overwrite_existing_workflow") is None and extracted.get("overwrite_existing_workflow"):
            merged_context["overwrite_existing_workflow"] = True
        return AgentTask(
            message=task.message,
            user_id=task.user_id,
            session_id=task.session_id,
            context=merged_context,
        )

    def _route(self, task: AgentTask) -> str:
        scores = self._scores(task)
        route, score = max(scores.items(), key=lambda item: item[1])
        return route if score > 0 else "unknown"

    @staticmethod
    def _scores(task: AgentTask) -> dict[str, int]:
        message = task.message.lower().strip()
        context = task.context
        scores = {"cli": 0, "cicd": 0, "diagnosis": 0, "github": 0}

        if any(term in message for term in ("docker", "container", "running containers")):
            scores["cli"] += 4
        if "docker logs" in message or "container logs" in message:
            scores["cli"] += 4

        if context.get("files"):
            scores["cicd"] += 3
        if any(
            term in message
            for term in (
                "generate workflow",
                "generate ci",
                "github actions yaml",
                "ci pipeline",
                "ci/cd pipeline",
                "detect stack",
                "repository analysis",
            )
        ):
            scores["cicd"] += 5

        if context.get("log_text"):
            scores["diagnosis"] += 5
        if any(
            term in message
            for term in (
                "analyze log",
                "diagnose failure",
                "why did ci fail",
                "error log",
                "failed workflow",
                "predict failure",
            )
        ):
            scores["diagnosis"] += 4
        if OrchestrationAgent._looks_like_error_log(message):
            scores["diagnosis"] += 3

        if context.get("repo_full_name"):
            scores["github"] += 3
        if any(
            term in message
            for term in (
                "github",
                "repository",
                "repo",
                "pull request",
                "workflow pr",
                "fix pr",
                "scan repo",
                "scan repository",
                "trigger workflow",
                "workflow run",
                "recent runs",
            )
        ):
            scores["github"] += 4
        if context.get("run_id") and ("diagnose" in message or "log" in message or "status" in message):
            scores["github"] += 5

        if "workflow pr" in message or "create pull request" in message:
            scores["github"] += 4
        if "create workflow" in message and context.get("repo_full_name"):
            scores["github"] += 4

        return scores

    @staticmethod
    def _extract_context(message: str) -> dict:
        context: dict[str, object] = {}
        repo_full_name = OrchestrationAgent._extract_repo_full_name(message)
        if repo_full_name:
            context["repo_full_name"] = repo_full_name

        run_id = OrchestrationAgent._extract_run_id(message)
        if run_id:
            context["run_id"] = run_id

        workflow_id = OrchestrationAgent._extract_workflow_id(message)
        if workflow_id:
            context["workflow_id"] = workflow_id

        ref = OrchestrationAgent._extract_ref(message)
        if ref:
            context["ref"] = ref

        container_name = OrchestrationAgent._extract_container_name(message)
        if container_name:
            context["container_name"] = container_name

        if any(term in message.lower() for term in ("overwrite", "replace existing", "update existing")):
            context["overwrite_existing_workflow"] = True

        if OrchestrationAgent._looks_like_error_log(message):
            context["log_text"] = message.strip()

        return context

    @staticmethod
    def _extract_repo_full_name(message: str) -> str | None:
        github_url = re.search(r"github\.com[:/]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", message)
        if github_url:
            repo = github_url.group(2).removesuffix(".git")
            return f"{github_url.group(1)}/{repo}"

        match = re.search(r"(?<![\w.-])([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?![\w.-])", message)
        if match:
            repo = match.group(1).removesuffix(".git")
            if not repo.startswith(("http:/", "https:/")):
                return repo
        return None

    @staticmethod
    def _extract_run_id(message: str) -> int | None:
        match = re.search(r"(?:run|run_id|workflow run)\s*(?:id|#|:)?\s*(\d{3,})", message, re.IGNORECASE)
        return int(match.group(1)) if match else None

    @staticmethod
    def _extract_workflow_id(message: str) -> str | None:
        match = re.search(
            r"(?:workflow|workflow_id)\s+(?!run\b)([A-Za-z0-9_.\-/]+\.ya?ml|\d+)",
            message,
            re.IGNORECASE,
        )
        return match.group(1) if match else None

    @staticmethod
    def _extract_ref(message: str) -> str | None:
        match = re.search(r"(?:branch|ref)\s+([A-Za-z0-9_.\-/]+)", message, re.IGNORECASE)
        return match.group(1).strip(".,") if match else None

    @staticmethod
    def _extract_container_name(message: str) -> str | None:
        match = re.search(r"(?:docker logs|container logs)\s+([A-Za-z0-9_.\-/]+)", message, re.IGNORECASE)
        return match.group(1).strip(".,") if match else None

    @staticmethod
    def _looks_like_error_log(message: str) -> bool:
        lowered = message.lower()
        error_markers = (
            "npm err",
            "error:",
            "traceback",
            "modulenotfounderror",
            "importerror",
            "pytest:",
            "command not found",
            "process completed with exit code",
            "failed",
            "exception",
        )
        return any(marker in lowered for marker in error_markers)
