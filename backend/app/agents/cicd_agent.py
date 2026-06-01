"""Specialized CI/CD Agent for stack detection and workflow generation."""
from __future__ import annotations

from typing import Any

from app.agents.agent_types import AgentResult, AgentTask
from app.services.repo_analyzer import detect_stack
from app.services.workflow_generator import WORKFLOW_PATH, generate_workflow


class CICDAgent:
    """Handle CI/CD stack analysis and offline workflow generation requests."""

    name = "cicd_agent"

    def handle(self, task: AgentTask) -> AgentResult:
        """Analyze repository files and optionally generate GitHub Actions YAML."""
        files = self._files_from_context(task.context)
        should_generate = self._is_workflow_generation_request(task.message)
        intent = "cicd_generate_workflow" if should_generate else "cicd_detect_stack"

        if not files:
            return AgentResult(
                selected_agent=self.name,
                intent=intent,
                risk_level="low",
                success=False,
                result="CI/CD Agent needs task.context['files'] with at least one repository file path.",
                metadata={},
            )

        try:
            stack = detect_stack(files)
            metadata: dict[str, Any] = {"stack": stack}

            if should_generate:
                workflow_yaml = generate_workflow(stack)
                metadata["workflow_yaml"] = workflow_yaml
                metadata["workflow_path"] = WORKFLOW_PATH
                summary = (
                    "Generated GitHub Actions workflow "
                    f"for {stack['language']} / {stack['framework']} project "
                    f"using {stack['recommended_workflow']}."
                )
            else:
                summary = (
                    "Detected project stack: "
                    f"{stack['language']} / {stack['framework']} "
                    f"with {stack['package_manager']} package management. "
                    f"Recommended workflow: {stack['recommended_workflow']}."
                )

            return AgentResult(
                selected_agent=self.name,
                intent=intent,
                risk_level="low",
                success=True,
                result=summary,
                metadata=metadata,
            )
        except Exception as exc:
            return AgentResult(
                selected_agent=self.name,
                intent=intent,
                risk_level="low",
                success=False,
                result=f"CI/CD Agent failed to process repository files: {exc}",
                metadata={},
            )

    @staticmethod
    def _files_from_context(context: dict[str, Any]) -> list[str]:
        raw_files = context.get("files")
        if not isinstance(raw_files, list):
            return []
        return [str(file).strip() for file in raw_files if str(file).strip()]

    @staticmethod
    def _is_workflow_generation_request(message: str) -> bool:
        normalized = message.lower()
        generation_phrases = (
            "generate ci workflow",
            "generate github actions workflow",
            "create ci pipeline",
        )
        return any(phrase in normalized for phrase in generation_phrases)
