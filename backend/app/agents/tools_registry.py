"""
DevOps Tools Registry
Registers all LangChain tools available to the agent.
Tools are filtered based on user role / RBAC.
"""
from langchain.tools import StructuredTool

from app.tools.docker_tool import (
    list_containers, start_container, stop_container,
    restart_container, get_container_logs, run_container
)
from app.tools.github_tool import (
    list_workflows, trigger_workflow, get_workflow_run_status, list_recent_runs
)
from app.tools.shell_tool import execute_safe_shell_command
from app.tools.monitoring_tool import get_system_metrics, get_service_health


def get_all_tools(user_role: str = "developer") -> list:
    """Return tools available to the given user role."""

    base_tools = [
        # ── Docker Tools ──────────────────────────────────────────────────────
        StructuredTool.from_function(
            func=list_containers,
            name="docker_list_containers",
            description="List all running Docker containers with their status, ports, and names.",
        ),
        StructuredTool.from_function(
            func=get_container_logs,
            name="docker_get_logs",
            description="Retrieve logs from a Docker container. Provide container_name and optional tail_lines.",
        ),
        StructuredTool.from_function(
            func=restart_container,
            name="docker_restart_container",
            description="Restart a Docker container by name. Use for self-healing when a service crashes.",
        ),

        # ── GitHub / CI/CD Tools ──────────────────────────────────────────────
        StructuredTool.from_function(
            func=list_workflows,
            name="github_list_workflows",
            description="List all GitHub Actions workflows in a repository.",
        ),
        StructuredTool.from_function(
            func=get_workflow_run_status,
            name="github_workflow_status",
            description="Get the status of a GitHub Actions workflow run.",
        ),
        StructuredTool.from_function(
            func=list_recent_runs,
            name="github_recent_runs",
            description="Get the most recent workflow runs with their status and conclusions.",
        ),

        # ── Monitoring Tools ──────────────────────────────────────────────────
        StructuredTool.from_function(
            func=get_system_metrics,
            name="get_system_metrics",
            description="Get current system metrics: CPU usage, memory, disk, and network I/O.",
        ),
        StructuredTool.from_function(
            func=get_service_health,
            name="get_service_health",
            description="Check the health status of a named service or endpoint.",
        ),
    ]

    # Operator/Admin-only tools
    elevated_tools = [
        StructuredTool.from_function(
            func=trigger_workflow,
            name="github_trigger_workflow",
            description="Trigger a GitHub Actions workflow dispatch event. HIGH RISK: requires approval for production.",
        ),
        StructuredTool.from_function(
            func=start_container,
            name="docker_start_container",
            description="Start a stopped Docker container.",
        ),
        StructuredTool.from_function(
            func=stop_container,
            name="docker_stop_container",
            description="Stop a running Docker container. HIGH RISK in production.",
        ),
        StructuredTool.from_function(
            func=run_container,
            name="docker_run_container",
            description="Run a new Docker container from an image. Specify image, name, ports, and environment.",
        ),
        StructuredTool.from_function(
            func=execute_safe_shell_command,
            name="execute_shell_command",
            description="Execute a safe, allowlisted shell command on the server. Only pre-approved commands are permitted.",
        ),
    ]

    if user_role in ("operator", "admin"):
        return base_tools + elevated_tools

    return base_tools
