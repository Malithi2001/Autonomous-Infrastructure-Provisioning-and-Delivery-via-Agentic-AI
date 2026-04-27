"""
GitHub Tool — LangChain tool functions for GitHub Actions CI/CD integration.
Uses PyGithub SDK.
"""
from github import Github, GithubException

from app.core.config import settings
from app.core.logging import logger

_gh_client = None


def _get_client() -> Github:
    global _gh_client
    if _gh_client is None:
        if not settings.GITHUB_TOKEN:
            raise RuntimeError("GITHUB_TOKEN is not configured.")
        _gh_client = Github(settings.GITHUB_TOKEN)
    return _gh_client


def list_workflows(repo_full_name: str) -> str:
    """List all workflows in a GitHub repository."""
    try:
        gh = _get_client()
        repo = gh.get_repo(repo_full_name)
        workflows = repo.get_workflows()
        if workflows.totalCount == 0:
            return f"No workflows found in '{repo_full_name}'."
        lines = [f"- [{w.state}] {w.name} (id: {w.id})" for w in workflows]
        return "\n".join(lines)
    except GithubException as e:
        return f"GitHub API error: {e.data.get('message', str(e))}"


def trigger_workflow(repo_full_name: str, workflow_id: str, ref: str = "main", inputs: dict = None) -> str:
    """Trigger a GitHub Actions workflow_dispatch event."""
    try:
        gh = _get_client()
        repo = gh.get_repo(repo_full_name)
        workflow = repo.get_workflow(workflow_id)
        success = workflow.create_dispatch(ref=ref, inputs=inputs or {})
        if success:
            logger.info("github.workflow.triggered", repo=repo_full_name, workflow=workflow_id, ref=ref)
            return f"✅ Workflow '{workflow_id}' triggered on branch '{ref}' in '{repo_full_name}'."
        return "Failed to trigger workflow."
    except GithubException as e:
        return f"GitHub API error: {e.data.get('message', str(e))}"


def get_workflow_run_status(repo_full_name: str, run_id: int) -> str:
    """Get status of a specific workflow run."""
    try:
        gh = _get_client()
        repo = gh.get_repo(repo_full_name)
        run = repo.get_workflow_run(run_id)
        return (
            f"Run #{run.run_number} — {run.name}\n"
            f"  Status: {run.status}\n"
            f"  Conclusion: {run.conclusion or 'in progress'}\n"
            f"  Branch: {run.head_branch}\n"
            f"  Started: {run.created_at}\n"
            f"  URL: {run.html_url}"
        )
    except GithubException as e:
        return f"GitHub API error: {e.data.get('message', str(e))}"


def list_recent_runs(repo_full_name: str, limit: int = 5) -> str:
    """List the most recent workflow runs for a repository."""
    try:
        gh = _get_client()
        repo = gh.get_repo(repo_full_name)
        runs = repo.get_workflow_runs()
        lines = []
        for run in list(runs)[:limit]:
            status_emoji = {"success": "✅", "failure": "❌", "cancelled": "⚠️"}.get(run.conclusion, "🔄")
            lines.append(
                f"{status_emoji} #{run.run_number}[{run.status}] {run.name} — {run.head_branch} ({run.created_at.strftime('%Y-%m-%d %H:%M')})"
            )
        return "\n".join(lines) if lines else "No workflow runs found."
    except GithubException as e:
        return f"GitHub API error: {e.data.get('message', str(e))}"
