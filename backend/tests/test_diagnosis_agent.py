"""Unit tests for the specialized Diagnosis Agent."""
from __future__ import annotations

from app.agents.agent_types import AgentTask
from app.agents.diagnosis_agent import DiagnosisAgent
from app.services.failure_prediction_service import FailurePredictionUnavailable


def test_diagnosis_agent_analyzes_npm_log_from_context(monkeypatch):
    def _predict(log_text: str) -> dict:
        assert log_text == "npm ERR! Missing script: test"
        return {
            "label": "npm_missing_test_script",
            "confidence": 0.82,
            "suggested_fix": "Add a test script or update the workflow to skip missing tests.",
        }

    def _recommend(label: str, log_text: str, repo_files: list[str] | None = None) -> dict:
        assert label == "npm_missing_test_script"
        assert repo_files == ["package.json", "src/App.jsx"]
        return {
            "summary": "The CI job ran npm test, but package.json does not define a test script.",
            "risk_level": "low",
            "safe_fix_available": True,
        }

    monkeypatch.setattr("app.agents.diagnosis_agent.failure_prediction_service.predict_failure", _predict)
    monkeypatch.setattr(
        "app.agents.diagnosis_agent.fix_recommendation_service.get_fix_recommendation",
        _recommend,
    )

    result = DiagnosisAgent().handle(
        AgentTask(
            message="analyze this log",
            context={
                "log_text": "npm ERR! Missing script: test",
                "files": ["package.json", "src/App.jsx"],
            },
        )
    )

    assert result.selected_agent == "diagnosis_agent"
    assert result.intent == "cicd_failure_diagnosis"
    assert result.risk_level == "low"
    assert result.success is True
    assert result.metadata["label"] == "npm_missing_test_script"
    assert result.metadata["confidence"] == 0.82
    assert result.metadata["suggested_fix"].startswith("Add a test script")
    assert result.metadata["recommendation"]["risk_level"] == "low"
    assert "82% confidence" in result.result


def test_diagnosis_agent_uses_message_when_it_contains_python_error(monkeypatch):
    log_text = "ModuleNotFoundError: No module named 'fastapi'"

    def _predict(value: str) -> dict:
        assert value == log_text
        return {
            "label": "python_missing_dependency",
            "confidence": 0.91,
            "suggested_fix": "Add the missing dependency to requirements.txt.",
        }

    def _recommend(label: str, value: str, repo_files: list[str] | None = None) -> dict:
        assert label == "python_missing_dependency"
        assert value == log_text
        return {
            "summary": "A Python dependency for 'fastapi' is missing during CI.",
            "risk_level": "low",
            "safe_fix_available": True,
        }

    monkeypatch.setattr("app.agents.diagnosis_agent.failure_prediction_service.predict_failure", _predict)
    monkeypatch.setattr(
        "app.agents.diagnosis_agent.fix_recommendation_service.get_fix_recommendation",
        _recommend,
    )

    result = DiagnosisAgent().handle(AgentTask(message=log_text))

    assert result.success is True
    assert result.metadata["label"] == "python_missing_dependency"
    assert result.metadata["confidence"] == 0.91
    assert "fastapi" in result.result


def test_diagnosis_agent_returns_clear_error_when_log_missing():
    result = DiagnosisAgent().handle(AgentTask(message="diagnose failure", context={}))

    assert result.selected_agent == "diagnosis_agent"
    assert result.intent == "cicd_failure_diagnosis"
    assert result.risk_level == "low"
    assert result.success is False
    assert "log_text" in result.result
    assert result.metadata == {}


def test_diagnosis_agent_handles_missing_model_safely(monkeypatch):
    def _unavailable(log_text: str) -> dict:
        raise FailurePredictionUnavailable("Failure prediction model not found at backend/app/ml/failure_model.joblib.")

    monkeypatch.setattr("app.agents.diagnosis_agent.failure_prediction_service.predict_failure", _unavailable)

    result = DiagnosisAgent().handle(
        AgentTask(message="predict failure", context={"log_text": "npm ERR! Missing script: test"})
    )

    assert result.success is False
    assert result.intent == "cicd_failure_diagnosis"
    assert "Failure diagnosis is unavailable" in result.result
    assert "failure_model.joblib" in result.result
    assert result.metadata == {}
