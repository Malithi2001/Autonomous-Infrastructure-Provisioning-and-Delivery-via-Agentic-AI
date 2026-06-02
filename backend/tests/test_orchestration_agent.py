"""Unit tests for the deterministic Orchestration Agent."""
from __future__ import annotations

from app.agents.agent_types import AgentResult, AgentTask
from app.agents.orchestration_agent import OrchestrationAgent


class _FakeAgent:
    def __init__(self, *, selected_agent: str, intent: str, result: str, metadata: dict | None = None) -> None:
        self.selected_agent = selected_agent
        self.intent = intent
        self.result = result
        self.metadata = metadata or {}
        self.received_task: AgentTask | None = None

    def handle(self, task: AgentTask) -> AgentResult:
        self.received_task = task
        return AgentResult(
            selected_agent=self.selected_agent,
            intent=self.intent,
            risk_level="low",
            success=True,
            result=self.result,
            metadata=self.metadata,
        )


def _agent(**kwargs) -> _FakeAgent:
    return _FakeAgent(**kwargs)


def test_orchestration_agent_routes_running_containers_to_cli_agent():
    cli_agent = _agent(
        selected_agent="cli_agent",
        intent="docker_list_containers",
        result="- [running] api (image: demo-api, ports: 8000->8000/tcp)",
        metadata={"tool_called": "list_containers"},
    )
    task = AgentTask(message="show running containers", user_id="user-1", session_id="session-1")

    result = OrchestrationAgent(cli_agent=cli_agent).handle(task)

    assert cli_agent.received_task == task
    assert result.selected_agent == "cli_agent"
    assert result.intent == "docker_list_containers"
    assert result.success is True
    assert result.metadata["tool_called"] == "list_containers"
    assert result.metadata["trace_steps"][1]["actor"] == "Orchestration Agent"
    assert result.metadata["trace_steps"][2]["actor"] == "CLI Agent"
    assert result.metadata["trace_steps"][3]["actor"] == "Docker Tool"


def test_orchestration_agent_routes_generate_workflow_to_cicd_agent():
    cicd_agent = _agent(
        selected_agent="cicd_agent",
        intent="cicd_generate_workflow",
        result="Generated GitHub Actions workflow.",
        metadata={"workflow_path": ".github/workflows/ai-generated-ci.yml"},
    )
    task = AgentTask(message="generate workflow", context={"files": ["package.json"]})

    result = OrchestrationAgent(cicd_agent=cicd_agent).handle(task)

    assert cicd_agent.received_task == task
    assert result.selected_agent == "cicd_agent"
    assert result.intent == "cicd_generate_workflow"
    assert result.metadata["workflow_path"] == ".github/workflows/ai-generated-ci.yml"
    assert result.metadata["trace_steps"][2]["actor"] == "CI/CD Agent"


def test_orchestration_agent_routes_failure_log_to_diagnosis_agent():
    diagnosis_agent = _agent(
        selected_agent="diagnosis_agent",
        intent="cicd_failure_diagnosis",
        result="Predicted CI/CD failure: npm_missing_test_script.",
        metadata={"label": "npm_missing_test_script"},
    )
    task = AgentTask(message="diagnose failure", context={"log_text": "npm ERR! Missing script: test"})

    result = OrchestrationAgent(diagnosis_agent=diagnosis_agent).handle(task)

    assert diagnosis_agent.received_task == task
    assert result.selected_agent == "diagnosis_agent"
    assert result.intent == "cicd_failure_diagnosis"
    assert result.metadata["label"] == "npm_missing_test_script"
    assert result.metadata["trace_steps"][2]["actor"] == "Diagnosis Agent"


def test_orchestration_agent_routes_repository_request_to_github_agent():
    github_agent = _agent(
        selected_agent="github_agent",
        intent="github_scan_repository",
        result="Scanned octo-org/demo-app.",
        metadata={"repo_full_name": "octo-org/demo-app"},
    )
    task = AgentTask(message="scan repo", context={"repo_full_name": "octo-org/demo-app"})

    result = OrchestrationAgent(github_agent=github_agent).handle(task)

    assert github_agent.received_task == task
    assert result.selected_agent == "github_agent"
    assert result.intent == "github_scan_repository"
    assert result.metadata["repo_full_name"] == "octo-org/demo-app"
    assert result.metadata["trace_steps"][2]["actor"] == "GitHub Agent"


def test_orchestration_agent_extracts_repo_and_overwrite_for_workflow_pr():
    github_agent = _agent(
        selected_agent="github_agent",
        intent="github_create_workflow_pr",
        result="Created workflow PR.",
        metadata={"repo_full_name": "octo-org/demo-app"},
    )
    task = AgentTask(message="create workflow PR for https://github.com/octo-org/demo-app and overwrite existing")

    result = OrchestrationAgent(github_agent=github_agent).handle(task)

    assert result.selected_agent == "github_agent"
    assert github_agent.received_task is not None
    assert github_agent.received_task.context["repo_full_name"] == "octo-org/demo-app"
    assert github_agent.received_task.context["overwrite_existing_workflow"] is True


def test_orchestration_agent_routes_workflow_run_diagnosis_to_github_agent():
    github_agent = _agent(
        selected_agent="github_agent",
        intent="github_diagnose_workflow_run",
        result="Diagnosed workflow run.",
        metadata={"run_id": 12345},
    )
    task = AgentTask(message="diagnose workflow run 12345 for octo-org/demo-app")

    result = OrchestrationAgent(github_agent=github_agent).handle(task)

    assert result.selected_agent == "github_agent"
    assert github_agent.received_task is not None
    assert github_agent.received_task.context["repo_full_name"] == "octo-org/demo-app"
    assert github_agent.received_task.context["run_id"] == 12345


def test_orchestration_agent_routes_fix_pr_request_to_github_agent():
    github_agent = _agent(
        selected_agent="github_agent",
        intent="github_create_fix_pr",
        result="Human approval is required before creating a fix PR.",
        metadata={"workflow_failure_id": 123},
    )
    task = AgentTask(message="create fix PR", context={"workflow_failure_id": 123})

    result = OrchestrationAgent(github_agent=github_agent).handle(task)

    assert github_agent.received_task == task
    assert result.selected_agent == "github_agent"
    assert result.intent == "github_create_fix_pr"
    assert result.metadata["workflow_failure_id"] == 123


def test_orchestration_agent_returns_unknown_for_unmatched_message():
    result = OrchestrationAgent().handle(
        AgentTask(message="explain what devops means")
    )

    assert result.selected_agent == "orchestration_agent"
    assert result.intent == "unknown"
    assert result.risk_level == "low"
    assert result.success is False
    assert result.result == "I could not route this request to a specialized agent."
    assert result.metadata["trace_steps"][0]["actor"] == "User"
    assert result.metadata["trace_steps"][1]["actor"] == "Orchestration Agent"
    assert result.metadata["trace_steps"][1]["status"] == "failed"
