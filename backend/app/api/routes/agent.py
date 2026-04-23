"""Agent chat endpoint."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.devops_agent import get_or_create_agent
from app.core.security import require_permission
from app.schemas.schemas import ChatRequest, ChatResponse

router = APIRouter()


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
        agent = get_or_create_agent(session_id=session_id, user_role=user_role)
        result = await agent.chat(request.message)

        return ChatResponse(
            output=result["output"],
            session_id=result["session_id"],
            intermediate_steps=[],  # Populated from result["intermediate_steps"] in full impl
        )
    except Exception as e:
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
