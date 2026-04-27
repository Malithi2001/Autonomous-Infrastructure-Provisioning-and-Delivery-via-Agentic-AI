"""
GitHub Tool — LangChain tool functions for GitHub Actions CI/CD integration.
Uses PyGithub SDK. Requires GITHUB_TOKEN in environment.
"""
from __future__ import annotations

from github import Github, GithubException

from app.core.config import settings
from app.core.logging import logger

_gh_client: Github | None = None


def _get_client() -> Github:
    global _gh_client
    if _gh_client is None:
        if not settings.GITHUB_TOKEN:
            raise RuntimeError(
                "GITHUB_TOKEN is not configured. "
                "Set it in backend/.env to enable GitHub integration."
            )
        _gh_client = Github(settings.GITHUB_TOKEN)
    return _gh_client


def _default_repo() -> str:
    repo = settings.GITHUB_REPO_FULL_NAME.strip()
    if not repo:
        raise RuntimeError(
            "No repository specified. Pass `owner/repo` or set "
            "GITHUB_REPO_FULL_NAME in backend/.env."
        )
    return repo


def list_workflows(repo_full_name: str = "") -> str:
    """List all workflows in a GitHub repository."""
    repo_full_name = repo_full_name or _default_repo()
    try:
        repo = _get_client().get_repo(repo_full_name)
        workflows = repo.get_workflows()
        if workflows.totalCount == 0:
            return f"No workflows found in '{repo_full_name}'."
        lines = [f"- [{w.state}] {w.name} (id: {w.id})" for w in workflows]
        return "\n".join(lines)
    except GithubException as e:
        return f"GitHub API error: {e.data.get('message', str(e))}"


def trigger_workflow(
    repo_full_name: str = "",
    workflow_id: str = "",
    ref: str = "main",
    inputs: dict | None = None,
) -> str:
    """Trigger a GitHub Actions workflow_dispatch event."""
    repo_full_name = repo_full_name or _default_repo()
    try:
        repo = _get_client().get_repo(repo_full_name)
        workflow = repo.get_workflow(workflow_id)
        success = workflow.create_dispatch(ref=ref, inputs=inputs or {})
        if success:
            logger.info(
                "github.workflow.triggered",
                repo=repo_full_name, workflow=workflow_id, ref=ref,
            )
            return f"✅ Workflow '{workflow_id}' triggered on branch '{ref}' in '{repo_full_name}'."
        return "Failed to trigger workflow — create_dispatch returned False."
    except GithubException as e:
        return f"GitHub API error: {e.data.get('message', str(e))}"


def get_workflow_run_status(repo_full_name: str = "", run_id: int = 0) -> str:
    """Get status of a specific workflow run."""
    repo_full_name = repo_full_name or _default_repo()
    try:
        repo = _get_client().get_repo(repo_full_name)
        run = repo.get_workflow_run(run_id)
        return (
            f"Run #{run.run_number} — {run.name}\n"
            f"  Status     : {run.status}\n"
            f"  Conclusion : {run.conclusion or 'in progress'}\n"
            f"  Branch     : {run.head_branch}\n"
            f"  Started    : {run.created_at}\n"
            f"  URL        : {run.html_url}"
        )
    except GithubException as e:
        return f"GitHub API error: {e.data.get('message', str(e))}"


def list_recent_runs(repo_full_name: str = "", limit: int = 5) -> str:
    """List the most recent workflow runs for a repository."""
    repo_full_name = repo_full_name or _default_repo()
    try:
        repo = _get_client().get_repo(repo_full_name)
        runs = repo.get_workflow_runs()
        lines = []
        for run in list(runs)[:limit]:
            emoji = {"success": "✅", "failure": "❌", "cancelled": "⚠️"}.get(
                run.conclusion, "🔄"
            )
            lines.append(
                f"{emoji} #{run.run_number} [{run.status}] {run.name} — "
                f"{run.head_branch} ({run.created_at.strftime('%Y-%m-%d %H:%M')})"
            )
        return "\n".join(lines) if lines else "No workflow runs found."
    except GithubException as e:
        return f"GitHub API error: {e.data.get('message', str(e))}"


def get_repo_info(repo_full_name: str = "") -> str:
    """Return basic metadata about a GitHub repository."""
    repo_full_name = repo_full_name or _default_repo()
    try:
        repo = _get_client().get_repo(repo_full_name)
        return (
            f"📦 {repo.full_name}\n"
            f"  Description  : {repo.description or '(none)'}\n"
            f"  Default branch: {repo.default_branch}\n"
            f"  Stars         : {repo.stargazers_count}\n"
            f"  Open issues   : {repo.open_issues_count}\n"
            f"  Last push     : {repo.pushed_at}\n"
            f"  URL           : {repo.html_url}"
        )
    except GithubException as e:
        return f"GitHub API error: {e.data.get('message', str(e))}"