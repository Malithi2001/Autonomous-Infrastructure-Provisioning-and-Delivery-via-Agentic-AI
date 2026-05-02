"""Agent chat and streaming endpoints."""
from __future__ import annotations

import asyncio
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.devops_agent import _agent_pool, get_or_create_agent
from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.security import decode_token, require_permission
from app.schemas.schemas import ChatRequest, ChatResponse
from app.services.execution_service import complete_execution, create_execution
from app.services.memory_service import DBChatMessageHistory

router = APIRouter()

_ws_connections: dict[str, set[WebSocket]] = {}
_MAX_CONNECTIONS_PER_USER = 5


def _is_openai_quota_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "insufficient_quota" in text or "exceeded your current quota" in text


def _is_ollama_connection_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "localhost" in text and "11434" in text and "connection refused" in text


def _raise_provider_errors(exc: Exception) -> None:
    if _is_openai_quota_error(exc):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "OpenAI API quota exceeded. Please check your OpenAI billing/quota "
                "or switch to another configured LLM provider."
            ),
        )
    if _is_ollama_connection_error(exc):
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
        detail=f"Agent error: {exc}",
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("agent:chat")),
):
    """Send a message to the LangChain agent and return its response."""
    session_id = request.session_id or str(uuid.uuid4())
    user_role = current_user.get("role", "developer")
    execution = None

    try:
        if settings.DEFAULT_LLM_PROVIDER.lower() != "test" or settings.MEMORY_BACKEND != "inmemory":
            execution = await create_execution(
                db,
                requested_by=current_user.get("username", current_user.get("sub", "unknown")),
                summary=request.message,
                source="agent",
            )
            # Do not hold a SQLite write lock while the agent/LLM is running.
            await db.commit()
        agent = get_or_create_agent(session_id=session_id, user_role=user_role)
        result = await agent.chat(request.message, db=db)
        if execution:
            await complete_execution(
                db,
                execution=execution,
                output=result["output"],
                intermediate_steps=result.get("intermediate_steps", []),
            )
        return ChatResponse(
    output=result["output"],
    session_id=result["session_id"],
    intermediate_steps=[
        {
            "tool": step[0].tool if hasattr(step[0], "tool") else str(step[0]),
            "input": step[0].tool_input if hasattr(step[0], "tool_input") else "",
            "output": str(step[1]),
        }
        for step in result.get("intermediate_steps", [])
    ],
    requires_approval=result.get("requires_approval"),
    approval_id=result.get("approval_id"),
)
    except HTTPException:
        raise
    except Exception as exc:
        _raise_provider_errors(exc)


@router.delete("/session/{session_id}", status_code=204)
async def clear_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("agent:chat")),
):
    """Clear the in-process agent instance and persisted history for a session."""
    _agent_pool.pop(session_id, None)
    history = DBChatMessageHistory(session_id=session_id, db=db)
    await history.aclear()
    await db.commit()
    return None


@router.websocket("/ws/agent")
async def agent_ws(
    websocket: WebSocket,
    session_id: Optional[str] = Query(default=None),
    token: Optional[str] = Query(default=None),
):
    """Stream agent tokens to the frontend over WebSocket."""
    if not token:
        await websocket.close(code=4001, reason="Missing auth token")
        return

    try:
        payload = decode_token(token)
        user_role = payload.get("role", "developer")
        user_id = payload.get("sub", "anonymous")
    except Exception:
        await websocket.close(code=4003, reason="Invalid or expired token")
        return

    user_connections = _ws_connections.setdefault(user_id, set())
    if len(user_connections) >= _MAX_CONNECTIONS_PER_USER:
        oldest = next(iter(user_connections))
        try:
            await oldest.close(code=1008, reason="Connection limit reached")
        except Exception:
            pass
        user_connections.discard(oldest)

    await websocket.accept()
    user_connections.add(websocket)

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=60)
            except asyncio.TimeoutError:
                await websocket.send_json({"event": "ping"})
                continue

            message = data.get("message", "").strip()
            ws_session_id = data.get("session_id") or session_id or str(uuid.uuid4())

            if not message:
                await websocket.send_json({"event": "error", "detail": "Empty message"})
                continue

            agent = get_or_create_agent(session_id=ws_session_id, user_role=user_role)
            try:
                async with AsyncSessionLocal() as db:
                    async for token_chunk in agent.stream_chat(message, db=db):
                        await websocket.send_text(token_chunk)
                    await db.commit()
                await websocket.send_json({"event": "done", "session_id": ws_session_id})
            except Exception as exc:
                await websocket.send_json({"event": "error", "detail": str(exc)})
    except WebSocketDisconnect:
        pass
    finally:
        user_connections.discard(websocket)
        if not user_connections:
            _ws_connections.pop(user_id, None)
