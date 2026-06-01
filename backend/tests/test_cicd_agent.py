"""Unit tests for the specialized CI/CD Agent."""
from __future__ import annotations

from app.agents.agent_types import AgentTask
from app.agents.cicd_agent import CICDAgent


def test_cicd_agent_generates_node_react_workflow():
    task = AgentTask(
        message="generate GitHub Actions workflow",
        context={"files": ["package.json", "package-lock.json", "src/App.jsx", "vite.config.js"]},
    )

    result = CICDAgent().handle(task)

    assert result.selected_agent == "cicd_agent"
    assert result.intent == "cicd_generate_workflow"
    assert result.risk_level == "low"
    assert result.success is True
    assert result.metadata["stack"]["language"] == "javascript"
    assert result.metadata["stack"]["framework"] == "react"
    assert result.metadata["stack"]["recommended_workflow"] == "node-ci"
    assert result.metadata["detected_project_count"] == 1
    assert result.metadata["ci_warning_count"] == 0
    assert result.metadata["workflow_path"] == ".github/workflows/ai-generated-ci.yml"
    assert "actions/setup-node@v4" in result.metadata["workflow_yaml"]
    assert "Generated GitHub Actions workflow" in result.result


def test_cicd_agent_detects_python_stack_without_generating_workflow():
    task = AgentTask(
        message="detect project stack",
        context={"files": ["requirements.txt\nfastapi==0.111.0", "app/main.py"]},
    )

    result = CICDAgent().handle(task)

    assert result.selected_agent == "cicd_agent"
    assert result.intent == "cicd_detect_stack"
    assert result.risk_level == "low"
    assert result.success is True
    assert result.metadata["stack"]["language"] == "python"
    assert result.metadata["stack"]["framework"] == "fastapi"
    assert result.metadata["stack"]["recommended_workflow"] == "python-ci"
    assert result.metadata["detected_project_count"] == 1
    assert "workflow_yaml" not in result.metadata
    assert "Detected project stack" in result.result


def test_cicd_agent_reports_existing_ci_warnings():
    task = AgentTask(
        message="detect project stack",
        context={
            "files": [
                "package.json",
                ".github/workflows/security.yml\n"
                "jobs:\n"
                "  dependency-review:\n"
                "    steps:\n"
                "      - uses: actions/dependency-review-action@v5\n",
            ]
        },
    )

    result = CICDAgent().handle(task)

    assert result.success is True
    assert result.metadata["ci_warning_count"] == 1
    assert "compatibility warning" in result.result


def test_cicd_agent_returns_clear_error_when_files_missing():
    result = CICDAgent().handle(AgentTask(message="analyze files", context={}))

    assert result.selected_agent == "cicd_agent"
    assert result.intent == "cicd_detect_stack"
    assert result.risk_level == "low"
    assert result.success is False
    assert "context['files']" in result.result
    assert result.metadata == {}
