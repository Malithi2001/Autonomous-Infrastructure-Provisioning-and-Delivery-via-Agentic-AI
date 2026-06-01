"""Specialized GitHub Agent for repository and workflow actions."""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.agent_types import AgentResult, AgentTask
from app.services.repo_analyzer import detect_stack
from app.services import failure_prediction_service, fix_pr_service, fix_recommendation_service
from app.services.fix_pr_service import FixPRServiceError
from app.services.failure_prediction_service import FailurePredictionError, FailurePredictionUnavailable
from app.tools import github_tool


class GitHubAgent:
    """Handle GitHub repository actions through existing safe tools/services."""

    name = "github_agent"

    def approval_plan(self, task: AgentTask) -> dict[str, Any] | None:
        """Return approval details for medium/high-risk GitHub actions before execution."""
        intent = self._intent(task.message)

        if intent == "github_create_workflow_pr":
            repo_full_name = self._repo_full_name(task)
            if not repo_full_name:
                return None
            risk_level = "medium"
            workflow_pr_details: dict[str, Any] = {
                "selected_agent": self.name,
                "intent": intent,
                "repository": repo_full_name,
                "overwrite_existing_workflow": bool(task.context.get("overwrite_existing_workflow")),
                "risk_level": risk_level,
                "proposed_tool_call": "github_create_workflow_pr",
                "action": "Create a branch, commit generated workflow YAML, and open a pull request.",
            }
            return {
                "selected_agent": self.name,
                "intent": intent,
                "risk_level": risk_level,
                "tool_name": "github_create_workflow_pr",
                "tool_input": {
                    "repo_full_name": repo_full_name,
                    "overwrite_existing_workflow": bool(task.context.get("overwrite_existing_workflow")),
                    "approval_details": workflow_pr_details,
                },
                "action": "Create GitHub Actions workflow pull request",
                "summary": f"Approve workflow PR creation for {repo_full_name}.",
                "details": workflow_pr_details,
            }

        if intent == "github_create_fix_pr":
            workflow_failure_id = task.context.get("workflow_failure_id")
            if workflow_failure_id in (None, ""):
                return None
            risk_level = "medium"
            fix_pr_details: dict[str, Any] = {
                "selected_agent": self.name,
                "intent": intent,
                "workflow_failure_id": workflow_failure_id,
                "risk_level": risk_level,
                "proposed_tool_call": "github_create_fix_pr",
                "action": "Create a branch, commit a safe workflow fix, and open a pull request.",
            }
            return {
                "selected_agent": self.name,
                "intent": intent,
                "risk_level": risk_level,
                "tool_name": "github_create_fix_pr",
                "tool_input": {
                    "workflow_failure_id": workflow_failure_id,
                    "approval_details": fix_pr_details,
                },
                "action": "Create GitHub fix pull request",
                "summary": f"Approve fix PR creation for workflow failure {workflow_failure_id}.",
                "details": fix_pr_details,
            }

        if intent == "github_trigger_workflow":
            repo_full_name = self._repo_full_name(task)
            workflow_id = self._workflow_id(task)
            if not repo_full_name or not workflow_id:
                return None
            ref = str(task.context.get("ref") or task.context.get("branch") or "main").strip()
            inputs = task.context.get("inputs") if isinstance(task.context.get("inputs"), dict) else None
            risk_level = "high" if self._is_production_or_deploy(task, workflow_id, ref) else "medium"
            trigger_details: dict[str, Any] = {
                "selected_agent": self.name,
                "intent": intent,
                "repository": repo_full_name,
                "workflow_id": workflow_id,
                "ref": ref,
                "inputs": inputs or {},
                "risk_level": risk_level,
                "proposed_tool_call": "github_trigger_workflow",
                "action": "Trigger a GitHub Actions workflow_dispatch event.",
            }
            return {
                "selected_agent": self.name,
                "intent": intent,
                "risk_level": risk_level,
                "tool_name": "github_trigger_workflow",
                "tool_input": {
                    "repo_full_name": repo_full_name,
                    "workflow_id": workflow_id,
                    "ref": ref,
                    "inputs": inputs or {},
                    "approval_details": trigger_details,
                },
                "action": "Trigger GitHub Actions workflow",
                "summary": f"Approve workflow trigger for {repo_full_name} workflow {workflow_id} on {ref}.",
                "details": trigger_details,
            }

        return None

    def handle(self, task: AgentTask) -> AgentResult:
        """Handle synchronous GitHub actions."""
        intent = self._intent(task.message)

        if intent == "github_scan_repository":
            return self._scan_repository(task)
        if intent == "github_create_workflow_pr":
            return self._create_workflow_pr(task)
        if intent == "github_list_workflows":
            return self._list_workflows(task)
        if intent == "github_recent_runs":
            return self._recent_runs(task)
        if intent == "github_workflow_status":
            return self._workflow_status(task)
        if intent == "github_download_workflow_logs":
            return self._download_workflow_logs(task)
        if intent == "github_diagnose_workflow_run":
            return self._diagnose_workflow_run(task)
        if intent == "github_trigger_workflow":
            return self._trigger_workflow(task)
        if intent == "github_create_fix_pr":
            return AgentResult(
                selected_agent=self.name,
                intent=intent,
                risk_level="medium",
                success=False,
                result="Creating a fix PR requires handle_async(..., db=...) so approval and audit rules can run.",
                metadata={},
            )

        return AgentResult(
            selected_agent=self.name,
            intent="unknown_github_intent",
            risk_level="low",
            success=False,
            result="GitHub Agent could not match this request to a supported GitHub operation.",
            metadata={},
        )

    async def handle_async(
        self,
        task: AgentTask,
        *,
        db: AsyncSession | None = None,
        current_user: dict | None = None,
    ) -> AgentResult:
        """Handle GitHub actions that require async services."""
        intent = self._intent(task.message)
        if intent != "github_create_fix_pr":
            return self.handle(task)

        if db is None:
            return AgentResult(
                selected_agent=self.name,
                intent=intent,
                risk_level="medium",
                success=False,
                result="Creating a fix PR requires a database session.",
                metadata={},
            )

        raw_workflow_failure_id = task.context.get("workflow_failure_id")
        if raw_workflow_failure_id in (None, ""):
            return AgentResult(
                selected_agent=self.name,
                intent=intent,
                risk_level="medium",
                success=False,
                result="workflow_failure_id is required in task.context to create a fix PR.",
                metadata={},
            )
        workflow_failure_id: str | int = (
            raw_workflow_failure_id
            if isinstance(raw_workflow_failure_id, (str, int))
            else str(raw_workflow_failure_id)
        )

        try:
            service_result = await fix_pr_service.create_fix_pr_for_failure(
                db,
                workflow_failure_id,
                current_user,
            )
            pull_request_url = service_result.get("pull_request_url")
            return AgentResult(
                selected_agent=self.name,
                intent=intent,
                risk_level="medium",
                success=bool(pull_request_url or service_result.get("approval_id")),
                result=self._fix_pr_summary(service_result),
                metadata=service_result,
            )
        except FixPRServiceError as exc:
            return AgentResult(
                selected_agent=self.name,
                intent=intent,
                risk_level="medium",
                success=False,
                result=f"Unable to create fix PR: {exc}",
                metadata={},
            )
        except Exception as exc:
            return AgentResult(
                selected_agent=self.name,
                intent=intent,
                risk_level="medium",
                success=False,
                result=f"GitHub Agent failed to create fix PR safely: {exc}",
                metadata={},
            )

    def _scan_repository(self, task: AgentTask) -> AgentResult:
        intent = "github_scan_repository"
        repo_full_name = self._repo_full_name(task)
        if not repo_full_name:
            return self._missing_repo(intent, risk_level="low")

        try:
            analysis = github_tool.get_repository_analysis_inputs(repo_full_name)
            files = analysis["files"]
            stack = detect_stack(analysis["analysis_inputs"])
            warning_count = len(stack.get("ci_warnings") or [])
            warning_text = f" Found {warning_count} CI compatibility warning(s)." if warning_count else ""
            return AgentResult(
                selected_agent=self.name,
                intent=intent,
                risk_level="low",
                success=True,
                result=(
                    f"Scanned {repo_full_name}: detected {stack['language']} / "
                    f"{stack['framework']} and recommended {stack['recommended_workflow']}.{warning_text}"
                ),
                metadata={
                    "repo_full_name": repo_full_name,
                    "file_count": len(files),
                    "files": files,
                    "stack": stack,
                    "tool_called": "get_repository_analysis_inputs",
                },
            )
        except Exception as exc:
            return self._failure(intent, "low", f"Unable to scan repository {repo_full_name}: {exc}")

    def _create_workflow_pr(self, task: AgentTask) -> AgentResult:
        intent = "github_create_workflow_pr"
        repo_full_name = self._repo_full_name(task)
        if not repo_full_name:
            return self._missing_repo(intent, risk_level="medium")

        try:
            overwrite_existing_workflow = bool(task.context.get("overwrite_existing_workflow"))
            result = github_tool.create_workflow_pr(
                repo_full_name,
                overwrite_existing_workflow=overwrite_existing_workflow,
            )
            pull_request_url = result.get("pull_request_url")
            return AgentResult(
                selected_agent=self.name,
                intent=intent,
                risk_level="medium",
                success=bool(pull_request_url),
                result=(
                    f"Created workflow pull request for {repo_full_name}: {pull_request_url}"
                    if pull_request_url
                    else f"Workflow PR request completed for {repo_full_name}."
                ),
                metadata={
                    **result,
                    "overwrite_existing_workflow": overwrite_existing_workflow,
                    "tool_called": "create_workflow_pr",
                },
            )
        except Exception as exc:
            return self._failure(intent, "medium", f"Unable to create workflow PR for {repo_full_name}: {exc}")

    def _list_workflows(self, task: AgentTask) -> AgentResult:
        intent = "github_list_workflows"
        repo_full_name = self._repo_full_name(task)
        if not repo_full_name:
            return self._missing_repo(intent, risk_level="low")

        result = github_tool.list_workflows(repo_full_name)
        success = not self._looks_like_tool_error(result)
        return AgentResult(
            selected_agent=self.name,
            intent=intent,
            risk_level="low",
            success=success,
            result=result,
            metadata={"repo_full_name": repo_full_name, "tool_called": "list_workflows"},
        )

    def _recent_runs(self, task: AgentTask) -> AgentResult:
        intent = "github_recent_runs"
        repo_full_name = self._repo_full_name(task)
        if not repo_full_name:
            return self._missing_repo(intent, risk_level="low")

        limit = self._limit(task)
        result = github_tool.list_recent_runs(repo_full_name, limit=limit)
        success = not self._looks_like_tool_error(result)
        return AgentResult(
            selected_agent=self.name,
            intent=intent,
            risk_level="low",
            success=success,
            result=result,
            metadata={"repo_full_name": repo_full_name, "limit": limit, "tool_called": "list_recent_runs"},
        )

    def _workflow_status(self, task: AgentTask) -> AgentResult:
        intent = "github_workflow_status"
        repo_full_name = self._repo_full_name(task)
        run_id = self._run_id(task)
        if not repo_full_name:
            return self._missing_repo(intent, risk_level="low")
        if not run_id:
            return self._missing_run_id(intent)

        result = github_tool.get_workflow_run_status(repo_full_name, run_id)
        success = not self._looks_like_tool_error(result)
        return AgentResult(
            selected_agent=self.name,
            intent=intent,
            risk_level="low",
            success=success,
            result=result,
            metadata={"repo_full_name": repo_full_name, "run_id": run_id, "tool_called": "get_workflow_run_status"},
        )

    def _download_workflow_logs(self, task: AgentTask) -> AgentResult:
        intent = "github_download_workflow_logs"
        repo_full_name = self._repo_full_name(task)
        run_id = self._run_id(task)
        if not repo_full_name:
            return self._missing_repo(intent, risk_level="low")
        if not run_id:
            return self._missing_run_id(intent)

        try:
            log_text = github_tool.download_workflow_logs(repo_full_name, run_id)
            return AgentResult(
                selected_agent=self.name,
                intent=intent,
                risk_level="low",
                success=True,
                result=f"Downloaded workflow logs for {repo_full_name} run {run_id}.",
                metadata={
                    "repo_full_name": repo_full_name,
                    "run_id": run_id,
                    "log_excerpt": log_text[:4000],
                    "log_chars": len(log_text),
                    "tool_called": "download_workflow_logs",
                },
            )
        except Exception as exc:
            return self._failure(intent, "low", f"Unable to download workflow logs for run {run_id}: {exc}")

    def _diagnose_workflow_run(self, task: AgentTask) -> AgentResult:
        intent = "github_diagnose_workflow_run"
        repo_full_name = self._repo_full_name(task)
        run_id = self._run_id(task)
        if not repo_full_name:
            return self._missing_repo(intent, risk_level="low")
        if not run_id:
            return self._missing_run_id(intent)

        try:
            log_text = github_tool.download_workflow_logs(repo_full_name, run_id)
            prediction = failure_prediction_service.predict_failure(log_text)
            label = str(prediction.get("label") or "unknown_failure")
            confidence = prediction.get("confidence")
            suggested_fix = str(prediction.get("suggested_fix") or "")
            recommendation = fix_recommendation_service.get_fix_recommendation(label, log_text, None)
            confidence_text = "unknown confidence" if confidence is None else f"{round(float(confidence) * 100)}%"
            return AgentResult(
                selected_agent=self.name,
                intent=intent,
                risk_level="low",
                success=True,
                result=(
                    f"Diagnosed {repo_full_name} run {run_id}: {label} "
                    f"({confidence_text}). Suggested fix: {suggested_fix}"
                ),
                metadata={
                    "repo_full_name": repo_full_name,
                    "run_id": run_id,
                    "label": label,
                    "confidence": confidence,
                    "suggested_fix": suggested_fix,
                    "recommendation": recommendation,
                    "log_excerpt": log_text[:4000],
                    "tool_called": ["download_workflow_logs", "predict_failure", "get_fix_recommendation"],
                },
            )
        except (FailurePredictionUnavailable, FailurePredictionError) as exc:
            return self._failure(intent, "low", f"Unable to diagnose workflow run {run_id}: {exc}")
        except Exception as exc:
            return self._failure(intent, "low", f"GitHub Agent failed to diagnose workflow run {run_id}: {exc}")

    def _trigger_workflow(self, task: AgentTask) -> AgentResult:
        intent = "github_trigger_workflow"
        repo_full_name = self._repo_full_name(task)
        workflow_id = self._workflow_id(task)
        ref = str(task.context.get("ref") or task.context.get("branch") or "main").strip()
        inputs = task.context.get("inputs") if isinstance(task.context.get("inputs"), dict) else None

        if not repo_full_name:
            return self._missing_repo(intent, risk_level="medium")
        if not workflow_id:
            return AgentResult(
                selected_agent=self.name,
                intent=intent,
                risk_level="medium",
                success=False,
                result="workflow_id or workflow_name is required in task.context to trigger a workflow.",
                metadata={},
            )

        risk_level = "high" if self._is_production_or_deploy(task, workflow_id, ref) else "medium"
        result = github_tool.trigger_workflow(repo_full_name, workflow_id, ref=ref, inputs=inputs)
        success = not self._looks_like_tool_error(result)
        return AgentResult(
            selected_agent=self.name,
            intent=intent,
            risk_level=risk_level,
            success=success,
            result=result,
            metadata={
                "repo_full_name": repo_full_name,
                "workflow_id": workflow_id,
                "ref": ref,
                "tool_called": "trigger_workflow",
            },
        )

    @staticmethod
    def _intent(message: str) -> str:
        normalized = message.lower()
        if "create fix pr" in normalized or "fix pr" in normalized:
            return "github_create_fix_pr"
        if (
            ("diagnose" in normalized or "analyze" in normalized)
            and ("workflow run" in normalized or "run " in normalized)
        ):
            return "github_diagnose_workflow_run"
        if "download logs" in normalized or "workflow logs" in normalized or "run logs" in normalized:
            return "github_download_workflow_logs"
        if "recent runs" in normalized or "latest runs" in normalized or "workflow runs" in normalized:
            return "github_recent_runs"
        if "run status" in normalized or "workflow status" in normalized or "status of run" in normalized:
            return "github_workflow_status"
        if "create workflow pr" in normalized or "workflow pr" in normalized:
            return "github_create_workflow_pr"
        if "scan repository" in normalized or "scan repo" in normalized:
            return "github_scan_repository"
        if "list workflows" in normalized:
            return "github_list_workflows"
        if "trigger workflow" in normalized:
            return "github_trigger_workflow"
        return "unknown_github_intent"

    @staticmethod
    def _repo_full_name(task: AgentTask) -> str:
        return str(task.context.get("repo_full_name") or "").strip()

    @staticmethod
    def _workflow_id(task: AgentTask) -> str:
        return str(
            task.context.get("workflow_id")
            or task.context.get("workflow_name")
            or task.context.get("workflow")
            or ""
        ).strip()

    @staticmethod
    def _run_id(task: AgentTask) -> int | None:
        raw_run_id = task.context.get("run_id") or task.context.get("workflow_run_id")
        if raw_run_id in (None, ""):
            return None
        try:
            return int(str(raw_run_id))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _limit(task: AgentTask) -> int:
        raw_limit = task.context.get("limit")
        try:
            limit = int(str(raw_limit))
        except (TypeError, ValueError):
            limit = 5
        return max(1, min(limit, 20))

    def _missing_repo(self, intent: str, *, risk_level: str) -> AgentResult:
        return AgentResult(
            selected_agent=self.name,
            intent=intent,
            risk_level=risk_level,
            success=False,
            result="repo_full_name is required in task.context for this GitHub operation.",
            metadata={},
        )

    def _missing_run_id(self, intent: str) -> AgentResult:
        return AgentResult(
            selected_agent=self.name,
            intent=intent,
            risk_level="low",
            success=False,
            result="run_id is required in task.context for this GitHub workflow-run operation.",
            metadata={},
        )

    def _failure(self, intent: str, risk_level: str, message: str) -> AgentResult:
        return AgentResult(
            selected_agent=self.name,
            intent=intent,
            risk_level=risk_level,
            success=False,
            result=message,
            metadata={},
        )

    @staticmethod
    def _looks_like_tool_error(result: str) -> bool:
        normalized = (result or "").lower()
        return normalized.startswith("github api error") or normalized.startswith("failed") or " error:" in normalized

    @staticmethod
    def _is_production_or_deploy(task: AgentTask, workflow_id: str, ref: str) -> bool:
        values = [
            task.message,
            workflow_id,
            ref,
            str(task.context.get("environment") or ""),
        ]
        combined = " ".join(values).lower()
        return any(marker in combined for marker in ("production", "prod", "deploy"))

    @staticmethod
    def _fix_pr_summary(service_result: dict[str, Any]) -> str:
        if service_result.get("pull_request_url"):
            return f"Created fix pull request: {service_result['pull_request_url']}"
        if service_result.get("approval_id"):
            return f"Fix PR requires human approval: {service_result['approval_id']}"
        return str(service_result.get("message") or "Fix PR request completed.")
