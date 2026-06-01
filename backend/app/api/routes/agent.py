"""Agent chat and streaming endpoints."""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.agent_types import AgentResult, AgentTask
from app.agents.devops_agent import _agent_pool, get_or_create_agent
from app.agents.orchestration_agent import OrchestrationAgent
from app.agents.tools_registry import HITLApprovalRequired
from app.api.routes.approvals import create_approval_request
from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.security import ACCESS_TOKEN_COOKIE_NAME, decode_token, has_permission, require_permission
from app.schemas.schemas import ChatRequest, ChatResponse, IntermediateStep
from app.services import audit_service
from app.services.execution_service import complete_execution, create_execution
from app.services.memory_service import DBChatMessageHistory
from app.core.logging import logger

router = APIRouter()

_ws_connections: dict[str, set[WebSocket]] = {}
_MAX_CONNECTIONS_PER_USER = 5


class OrchestrationRequest(BaseModel):
    """Request body for deterministic multi-agent orchestration tests."""

    message: str
    context: dict[str, Any] = Field(default_factory=dict)


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
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Agent error: {exc}")


def _serialize_intermediate_steps(steps: list) -> list[IntermediateStep]:
    serialized: list[IntermediateStep] = []
    for step in steps:
        try:
            action, output = step
            serialized.append(
                IntermediateStep(
                    tool=action.tool if hasattr(action, "tool") else str(action),
                    input=action.tool_input if hasattr(action, "tool_input") else "",
                    output=str(output),
                )
            )
        except Exception:
            serialized.append(IntermediateStep(tool="unknown", input="", output=str(step)))
    return serialized


@router.post("/orchestrate", response_model=AgentResult)
async def orchestrate(
    request: OrchestrationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("agent:chat")),
):
    """Route a request through the deterministic multi-agent orchestration layer."""
    actor = current_user.get("username") or current_user.get("sub") or "unknown"
    task = AgentTask(
        message=request.message,
        user_id=current_user.get("sub"),
        session_id=request.context.get("session_id"),
        context=request.context,
    )
    try:
        orchestrator = OrchestrationAgent()
        approval_plan = orchestrator.approval_plan(task)
        if approval_plan:
            approval = await create_approval_request(
                db=db,
                session_id=task.session_id or str(uuid.uuid4()),
                requested_by=actor,
                tool_name=approval_plan["tool_name"],
                tool_input=approval_plan["tool_input"],
                action=approval_plan["action"],
                risk_level=approval_plan["risk_level"],
                summary=approval_plan["summary"],
                timeout_seconds=settings.HITL_APPROVAL_TIMEOUT_SECONDS,
            )
            result = AgentResult(
                selected_agent=approval_plan["selected_agent"],
                intent=approval_plan["intent"],
                risk_level=approval_plan["risk_level"],
                success=False,
                result=(
                    "Human approval is required before executing this action. "
                    f"Approval request {approval.id} is pending."
                ),
                metadata={
                    "approval_required": True,
                    "approval_id": approval.id,
                    "proposed_tool_call": approval_plan["tool_name"],
                    "approval_details": approval_plan["details"],
                },
            )
        else:
            result = orchestrator.handle(task)
        try:
            await audit_service.log_multi_agent_execution(
                db,
                message=request.message,
                context=request.context,
                selected_agent=result.selected_agent,
                intent=result.intent,
                risk_level=result.risk_level,
                success=result.success,
                result=result.result,
                metadata=result.metadata,
                actor=actor,
                user_id=current_user.get("sub"),
                session_id=task.session_id,
                source="api",
            )
        except audit_service.AuditError as audit_exc:
            await db.rollback()
            logger.warning("audit.multi_agent.skipped", error=str(audit_exc))
        return result
    except HTTPException:
        raise
    except Exception as exc:
        safe_error = "Agent orchestration failed. Please try again."
        try:
            await audit_service.log_multi_agent_execution(
                db,
                message=request.message,
                context=request.context,
                selected_agent="orchestration_agent",
                intent="orchestration_error",
                risk_level="low",
                success=False,
                result=safe_error,
                metadata={"error_type": exc.__class__.__name__},
                actor=actor,
                user_id=current_user.get("sub"),
                session_id=task.session_id,
                source="api",
            )
        except audit_service.AuditError as audit_exc:
            await db.rollback()
            logger.warning("audit.multi_agent_error.skipped", error=str(audit_exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=safe_error,
        ) from exc


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
            await db.commit()

        agent = get_or_create_agent(session_id=session_id, user_role=user_role)
        try:
            result = await agent.chat(request.message, db=db)
        except HITLApprovalRequired as approval_exc:
            approval = await create_approval_request(
                db=db,
                session_id=session_id,
                requested_by=current_user.get("username", current_user.get("sub", "unknown")),
                tool_name=approval_exc.tool_name,
                tool_input=approval_exc.tool_input,
                action=approval_exc.summary,
                risk_level=approval_exc.risk_level,
                summary=approval_exc.summary,
                timeout_seconds=settings.HITL_APPROVAL_TIMEOUT_SECONDS,
            )
            if execution:
                execution.status = "pending"
                execution.summary = f"Approval required: {approval_exc.summary}"
                execution.details = json.dumps(
                    {
                        "approval_id": approval.id,
                        "tool_name": approval_exc.tool_name,
                        "risk_level": approval_exc.risk_level,
                        "tool_input": approval_exc.tool_input,
                    },
                    ensure_ascii=False,
                )
                execution.approval_id = approval.id
                await db.flush()
            await db.commit()
            return ChatResponse(
                output=(
                    f"Approval required before running `{approval_exc.tool_name}`. "
                    f"Risk level: {approval_exc.risk_level}. {approval_exc.summary}"
                ),
                session_id=session_id,
                intermediate_steps=[],
                requires_approval=True,
                approval_id=approval.id,
            )

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
            intermediate_steps=_serialize_intermediate_steps(result.get("intermediate_steps", [])),
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
    """Stream agent tokens to the frontend over WebSocket using cookie auth when available."""
    auth_header = websocket.headers.get("authorization", "")
    bearer_token = auth_header.split(" ", 1)[1].strip() if auth_header.lower().startswith("bearer ") else None
    websocket_token = token or bearer_token or websocket.cookies.get(ACCESS_TOKEN_COOKIE_NAME)

    if not websocket_token:
        await websocket.close(code=4001, reason="Missing auth token")
        return

    try:
        payload = decode_token(websocket_token)
        if payload.get("type") != "access":
            await websocket.close(code=4003, reason="Invalid token type")
            return
        user_role = payload.get("role", "developer")
        if not has_permission(user_role, "agent:chat"):
            await websocket.close(code=4003, reason="Agent chat permission required")
            return
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
