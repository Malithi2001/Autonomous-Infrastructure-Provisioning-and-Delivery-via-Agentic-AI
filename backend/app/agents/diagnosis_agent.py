"""Specialized Diagnosis Agent for CI/CD failure logs."""
from __future__ import annotations

from typing import Any

from app.agents.agent_types import AgentResult, AgentTask
from app.services import failure_prediction_service, fix_recommendation_service
from app.services.failure_prediction_service import FailurePredictionError, FailurePredictionUnavailable


class DiagnosisAgent:
    """Analyze CI/CD logs with the trained failure classifier."""

    name = "diagnosis_agent"

    def handle(self, task: AgentTask) -> AgentResult:
        """Predict the failure label and return a fix recommendation."""
        log_text = self._log_text_from_task(task)
        if not log_text:
            return AgentResult(
                selected_agent=self.name,
                intent="cicd_failure_diagnosis",
                risk_level="low",
                success=False,
                result=(
                    "Diagnosis Agent needs task.context['log_text'] or a message containing "
                    "recognizable CI/CD error text."
                ),
                metadata={},
            )

        try:
            prediction = failure_prediction_service.predict_failure(log_text)
            label = str(prediction.get("label") or "unknown_failure")
            confidence = prediction.get("confidence")
            suggested_fix = str(prediction.get("suggested_fix") or "")
            recommendation = self._build_recommendation(label, log_text, task.context, prediction)

            return AgentResult(
                selected_agent=self.name,
                intent="cicd_failure_diagnosis",
                risk_level="low",
                success=True,
                result=self._summary(label, confidence, suggested_fix, recommendation),
                metadata={
                    "label": label,
                    "confidence": confidence,
                    "suggested_fix": suggested_fix,
                    "recommendation": recommendation,
                },
            )
        except FailurePredictionUnavailable as exc:
            return AgentResult(
                selected_agent=self.name,
                intent="cicd_failure_diagnosis",
                risk_level="low",
                success=False,
                result=f"Failure diagnosis is unavailable: {exc}",
                metadata={},
            )
        except FailurePredictionError as exc:
            return AgentResult(
                selected_agent=self.name,
                intent="cicd_failure_diagnosis",
                risk_level="low",
                success=False,
                result=f"Failure diagnosis failed: {exc}",
                metadata={},
            )
        except Exception as exc:
            return AgentResult(
                selected_agent=self.name,
                intent="cicd_failure_diagnosis",
                risk_level="low",
                success=False,
                result=f"Diagnosis Agent failed to analyze the log safely: {exc}",
                metadata={},
            )

    def _build_recommendation(
        self,
        label: str,
        log_text: str,
        context: dict[str, Any],
        prediction: dict[str, Any],
    ) -> dict[str, Any] | None:
        repo_files = self._repo_files_from_context(context)
        try:
            return fix_recommendation_service.get_fix_recommendation(label, log_text, repo_files)
        except Exception:
            fallback = prediction.get("recommendation")
            return fallback if isinstance(fallback, dict) else None

    @staticmethod
    def _log_text_from_task(task: AgentTask) -> str:
        context_log = str(task.context.get("log_text") or "").strip()
        if context_log:
            return context_log

        message = (task.message or "").strip()
        return message if DiagnosisAgent._looks_like_error_log(message) else ""

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
            "failed",
            "exception",
        )
        return any(marker in lowered for marker in error_markers)

    @staticmethod
    def _repo_files_from_context(context: dict[str, Any]) -> list[str] | None:
        raw_files = context.get("files")
        if not isinstance(raw_files, list):
            return None
        files = [str(file).strip() for file in raw_files if str(file).strip()]
        return files or None

    @staticmethod
    def _summary(
        label: str,
        confidence: Any,
        suggested_fix: str,
        recommendation: dict[str, Any] | None,
    ) -> str:
        confidence_text = (
            "unknown confidence"
            if confidence is None
            else f"{round(float(confidence) * 100)}% confidence"
        )
        parts = [f"Predicted CI/CD failure: {label} ({confidence_text})."]
        if suggested_fix:
            parts.append(f"Suggested fix: {suggested_fix}")
        if recommendation and recommendation.get("summary"):
            parts.append(f"Recommendation: {recommendation['summary']}")
        return " ".join(parts)
