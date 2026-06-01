"""Unit tests for the specialized GitHub Agent."""
from __future__ import annotations

import pytest

from app.agents.agent_types import AgentTask
from app.agents.github_agent import GitHubAgent


def test_github_agent_scans_repository_with_mocked_tree(monkeypatch):
    monkeypatch.setattr(
        "app.agents.github_agent.github_tool.get_repository_analysis_inputs",
        lambda repo_full_name: {
            "files": ["package.json", "src/App.jsx", "vite.config.js"],
            "analysis_inputs": ["package.json", "src/App.jsx", "vite.config.js"],
        },
    )

    result = GitHubAgent().handle(
        AgentTask(message="scan repository", context={"repo_full_name": "octo-org/demo-app"})
    )

    assert result.selected_agent == "github_agent"
    assert result.intent == "github_scan_repository"
    assert result.risk_level == "low"
    assert result.success is True
    assert result.metadata["repo_full_name"] == "octo-org/demo-app"
    assert result.metadata["stack"]["language"] == "javascript"
    assert result.metadata["stack"]["framework"] == "react"
    assert result.metadata["tool_called"] == "get_repository_analysis_inputs"


def test_github_agent_creates_workflow_pr_with_medium_risk(monkeypatch):
    captured: dict[str, object] = {}

    def _create_workflow_pr(repo_full_name: str, *, overwrite_existing_workflow: bool = False):
        captured["overwrite_existing_workflow"] = overwrite_existing_workflow
        return {
            "repo_full_name": repo_full_name,
            "detected_stack": {"language": "python", "recommended_workflow": "python-ci"},
            "branch": "ai-cicd/setup-pipeline",
            "workflow_path": ".github/workflows/ai-generated-ci.yml",
            "pull_request_url": "https://github.com/octo-org/demo-app/pull/7",
        }

    monkeypatch.setattr(
        "app.agents.github_agent.github_tool.create_workflow_pr",
        _create_workflow_pr,
    )

    result = GitHubAgent().handle(
        AgentTask(
            message="create workflow PR",
            context={
                "repo_full_name": "octo-org/demo-app",
                "overwrite_existing_workflow": True,
            },
        )
    )

    assert result.intent == "github_create_workflow_pr"
    assert result.risk_level == "medium"
    assert result.success is True
    assert result.metadata["pull_request_url"] == "https://github.com/octo-org/demo-app/pull/7"
    assert result.metadata["overwrite_existing_workflow"] is True
    assert result.metadata["tool_called"] == "create_workflow_pr"
    assert captured["overwrite_existing_workflow"] is True


def test_github_agent_lists_workflows(monkeypatch):
    monkeypatch.setattr(
        "app.agents.github_agent.github_tool.list_workflows",
        lambda repo_full_name: "- [active] CI (id: 123)",
    )

    result = GitHubAgent().handle(
        AgentTask(message="list workflows", context={"repo_full_name": "octo-org/demo-app"})
    )

    assert result.intent == "github_list_workflows"
    assert result.risk_level == "low"
    assert result.success is True
    assert "CI" in result.result
    assert result.metadata["tool_called"] == "list_workflows"


def test_github_agent_lists_recent_runs(monkeypatch):
    monkeypatch.setattr(
        "app.agents.github_agent.github_tool.list_recent_runs",
        lambda repo_full_name, limit=5: f"recent runs for {repo_full_name} limit={limit}",
    )

    result = GitHubAgent().handle(
        AgentTask(message="show recent runs", context={"repo_full_name": "octo-org/demo-app", "limit": 3})
    )

    assert result.intent == "github_recent_runs"
    assert result.success is True
    assert "limit=3" in result.result
    assert result.metadata["tool_called"] == "list_recent_runs"


def test_github_agent_gets_workflow_run_status(monkeypatch):
    monkeypatch.setattr(
        "app.agents.github_agent.github_tool.get_workflow_run_status",
        lambda repo_full_name, run_id: f"Run {run_id} status for {repo_full_name}",
    )

    result = GitHubAgent().handle(
        AgentTask(message="run status", context={"repo_full_name": "octo-org/demo-app", "run_id": 12345})
    )

    assert result.intent == "github_workflow_status"
    assert result.success is True
    assert result.metadata["run_id"] == 12345
    assert result.metadata["tool_called"] == "get_workflow_run_status"


def test_github_agent_diagnoses_workflow_run(monkeypatch):
    monkeypatch.setattr(
        "app.agents.github_agent.github_tool.download_workflow_logs",
        lambda repo_full_name, run_id: "npm ERR! Missing script: test",
    )
    monkeypatch.setattr(
        "app.agents.github_agent.failure_prediction_service.predict_failure",
        lambda log_text: {
            "label": "npm_missing_test_script",
            "confidence": 0.91,
            "suggested_fix": "Add a test script.",
        },
    )
    monkeypatch.setattr(
        "app.agents.github_agent.fix_recommendation_service.get_fix_recommendation",
        lambda label, log_text, files: {"summary": "Missing npm test script"},
    )

    result = GitHubAgent().handle(
        AgentTask(
            message="diagnose workflow run",
            context={"repo_full_name": "octo-org/demo-app", "run_id": 12345},
        )
    )

    assert result.intent == "github_diagnose_workflow_run"
    assert result.success is True
    assert result.metadata["label"] == "npm_missing_test_script"
    assert result.metadata["run_id"] == 12345


def test_github_agent_trigger_workflow_requires_workflow_identifier():
    result = GitHubAgent().handle(
        AgentTask(message="trigger workflow", context={"repo_full_name": "octo-org/demo-app"})
    )

    assert result.intent == "github_trigger_workflow"
    assert result.risk_level == "medium"
    assert result.success is False
    assert "workflow_id or workflow_name" in result.result


def test_github_agent_trigger_production_workflow_is_high_risk(monkeypatch):
    captured = {}

    def _trigger(repo_full_name: str, workflow_id: str, ref: str = "main", inputs: dict | None = None) -> str:
        captured.update({"repo": repo_full_name, "workflow_id": workflow_id, "ref": ref, "inputs": inputs})
        return "Workflow triggered"

    monkeypatch.setattr("app.agents.github_agent.github_tool.trigger_workflow", _trigger)

    result = GitHubAgent().handle(
        AgentTask(
            message="trigger workflow for production deploy",
            context={
                "repo_full_name": "octo-org/demo-app",
                "workflow_id": "deploy.yml",
                "ref": "main",
                "inputs": {"environment": "production"},
            },
        )
    )

    assert result.intent == "github_trigger_workflow"
    assert result.risk_level == "high"
    assert result.success is True
    assert captured["workflow_id"] == "deploy.yml"
    assert result.metadata["tool_called"] == "trigger_workflow"


@pytest.mark.asyncio
async def test_github_agent_creates_fix_pr_with_async_service(monkeypatch):
    async def _create_fix_pr_for_failure(db, workflow_failure_id, current_user):
        assert db == "db-session"
        assert workflow_failure_id == 123
        assert current_user == {"username": "operator"}
        return {
            "workflow_failure_id": "123",
            "repo_full_name": "octo-org/demo-app",
            "status": "fix_pr_created",
            "pull_request_url": "https://github.com/octo-org/demo-app/pull/12",
            "message": "Created safe fix PR.",
        }

    monkeypatch.setattr(
        "app.agents.github_agent.fix_pr_service.create_fix_pr_for_failure",
        _create_fix_pr_for_failure,
    )

    result = await GitHubAgent().handle_async(
        AgentTask(message="create fix PR", context={"workflow_failure_id": 123}),
        db="db-session",
        current_user={"username": "operator"},
    )

    assert result.intent == "github_create_fix_pr"
    assert result.risk_level == "medium"
    assert result.success is True
    assert result.metadata["pull_request_url"] == "https://github.com/octo-org/demo-app/pull/12"
    assert "Created fix pull request" in result.result


@pytest.mark.asyncio
async def test_github_agent_create_fix_pr_requires_db_session():
    result = await GitHubAgent().handle_async(
        AgentTask(message="create fix PR", context={"workflow_failure_id": 123})
    )

    assert result.intent == "github_create_fix_pr"
    assert result.risk_level == "medium"
    assert result.success is False
    assert "database session" in result.result
