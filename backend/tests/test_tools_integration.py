"""Integration tests for the agent HTTP and WebSocket surfaces."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app


def _auth_headers() -> dict[str, str]:
    token = create_access_token(
        {
            "sub": "integration-user",
            "username": "integration-user",
            "role": "developer",
        }
    )
    return {"Authorization": f"Bearer {token}"}


def test_agent_chat_retains_context_across_three_messages(monkeypatch):
    from app.agents.devops_agent import _agent_pool
    from app.core.config import settings

    monkeypatch.setattr(settings, "DEFAULT_LLM_PROVIDER", "test")
    monkeypatch.setattr(settings, "MEMORY_BACKEND", "inmemory")
    session_id = f"chat-it-{uuid.uuid4()}"

    with TestClient(app) as client:
        response_1 = client.post(
            "/api/agent/chat",
            headers=_auth_headers(),
            json={"session_id": session_id, "message": "Hello from the first message."},
        )
        response_2 = client.post(
            "/api/agent/chat",
            headers=_auth_headers(),
            json={"session_id": session_id, "message": "This is my second message."},
        )
        response_3 = client.post(
            "/api/agent/chat",
            headers=_auth_headers(),
            json={"session_id": session_id, "message": "What was my first message?"},
        )

    assert response_1.status_code == 200
    assert response_2.status_code == 200
    assert response_3.status_code == 200
    assert response_3.json()["session_id"] == session_id
    assert "Hello from the first message." in response_3.json()["output"]

    _agent_pool.pop(session_id, None)


def test_agent_websocket_streams_tokens(monkeypatch):
    from app.agents.devops_agent import _agent_pool
    from app.core.config import settings

    monkeypatch.setattr(settings, "DEFAULT_LLM_PROVIDER", "test")
    monkeypatch.setattr(settings, "MEMORY_BACKEND", "inmemory")

    token = create_access_token(
        {
            "sub": "ws-user",
            "username": "ws-user",
            "role": "developer",
        }
    )
    session_id = f"ws-it-{uuid.uuid4()}"

    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/agent?token={token}&session_id={session_id}") as websocket:
            websocket.send_json({"message": "Stream this reply.", "session_id": session_id})

            expected = "Test agent received: Stream this reply."
            chunks = [websocket.receive_text() for _ in expected]
            done = websocket.receive_json()

    assert "".join(chunks) == expected
    assert done == {"event": "done", "session_id": session_id}
    _agent_pool.pop(session_id, None)
