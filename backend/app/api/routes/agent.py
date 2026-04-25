"""Agent chat endpoint."""
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.devops_agent import get_or_create_agent
from app.core.config import settings
from app.core.security import require_permission
from app.schemas.schemas import ChatRequest, ChatResponse
from app.tools.docker_tool import list_containers, restart_container
from app.tools.github_tool import list_recent_runs
from app.tools.monitoring_tool import get_service_health, get_system_metrics

router = APIRouter()


def _is_system_metrics_request(message: str) -> bool:
    text = message.lower()
    return (
        any(term in text for term in ("cpu", "memory", "ram", "system metrics"))
        and any(term in text for term in ("usage", "check", "show", "get"))
    )


def _is_service_health_request(message: str) -> bool:
    text = message.lower()
    return (
        any(term in text for term in ("health", "healthy", "status"))
        and re.search(r"https?://\S+", message) is not None
    )


def _url_from_message(message: str) -> str:
    match = re.search(r"https?://\S+", message)
    return match.group(0).rstrip(".,)") if match else ""


def _is_openai_quota_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "insufficient_quota" in text or "exceeded your current quota" in text


def _is_ollama_connection_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "localhost" in text and "11434" in text and "connection refused" in text


def _is_docker_list_request(message: str) -> bool:
    text = message.lower()
    return (
        "docker" in text
        and "container" in text
        and any(term in text for term in ("list", "show", "running"))
    )


def _is_docker_restart_request(message: str) -> bool:
    text = message.lower()
    return "restart" in text and "container" in text


def _container_name_from_restart_message(message: str) -> str:
    patterns = [
        r"\brestart\s+(?:the\s+)?([\w.-]+)\s+container\b",
        r"\brestart\s+(?:the\s+)?container\s+([\w.-]+)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def _is_recent_github_runs_request(message: str) -> bool:
    text = message.lower()
    return (
        "github" in text
        and any(term in text for term in ("workflow", "actions"))
        and any(term in text for term in ("recent", "runs", "run"))
    )


def _repo_from_message(message: str) -> str:
    match = re.search(r"\b([\w.-]+/[\w.-]+)\b", message)
    return match.group(1) if match else settings.GITHUB_REPO_FULL_NAME.strip()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(require_permission("agent:chat")),
):
    """
    Send a natural language message to the DevOps agent.
    The agent will plan, reason, and execute the appropriate DevOps actions.
    """
    session_id = request.session_id or str(uuid.uuid4())
    user_role = current_user.get("role", "developer")

    try:
        if _is_system_metrics_request(request.message):
            return ChatResponse(
                output=get_system_metrics(),
                session_id=session_id,
                intermediate_steps=[],
            )

        if _is_service_health_request(request.message):
            url = _url_from_message(request.message)
            return ChatResponse(
                output=get_service_health(url=url, service_name=url),
                session_id=session_id,
                intermediate_steps=[],
            )

        if _is_recent_github_runs_request(request.message):
            repo_full_name = _repo_from_message(request.message)
            if not repo_full_name:
                output = (
                    "Please include a GitHub repository as `owner/repo`, or set "
                    "`GITHUB_REPO_FULL_NAME=owner/repo` in backend/.env."
                )
            else:
                output = list_recent_runs(repo_full_name)
            return ChatResponse(
                output=output,
                session_id=session_id,
                intermediate_steps=[],
            )

        if _is_docker_list_request(request.message):
            try:
                output = list_containers(all_containers=False)
            except RuntimeError as exc:
                output = str(exc)
            return ChatResponse(
                output=output,
                session_id=session_id,
                intermediate_steps=[],
            )

        if _is_docker_restart_request(request.message):
            container_name = _container_name_from_restart_message(request.message)
            if not container_name:
                output = "Please include the container name, for example: `Restart the nginx container`."
            else:
                try:
                    output = restart_container(container_name)
                except RuntimeError as exc:
                    output = str(exc)
            return ChatResponse(
                output=output,
                session_id=session_id,
                intermediate_steps=[],
            )

        agent = get_or_create_agent(session_id=session_id, user_role=user_role)
        result = await agent.chat(request.message)

        return ChatResponse(
            output=result["output"],
            session_id=result["session_id"],
            intermediate_steps=[],  # Populated from result["intermediate_steps"] in full impl
        )
    except Exception as e:
        if _is_openai_quota_error(e):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "OpenAI API quota exceeded. Please check your OpenAI billing/quota "
                    "or switch to another configured LLM provider."
                ),
            )

        if _is_ollama_connection_error(e):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Ollama is not running at http://localhost:11434. Start it with "
                    "`ollama serve`, then pull the configured model with "
                    f"`ollama pull {settings.DEFAULT_MODEL}`."
                ),
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent error: {str(e)}",
        )


@router.delete("/session/{session_id}", status_code=204)
async def clear_session(
    session_id: str,
    current_user: dict = Depends(require_permission("agent:chat")),
):
    """Clear an agent conversation session."""
    from app.agents.devops_agent import _agent_pool
    _agent_pool.pop(session_id, None)
    return None
