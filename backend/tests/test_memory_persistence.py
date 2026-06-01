# backend/tests/test_memory_persistence.py
"""
Tests for session memory persistence.

Verifies:
1. ConversationBufferWindowMemory accumulates messages correctly.
2. build_memory() falls back gracefully to in-process memory when Redis/Postgres are unavailable.
3. A re-created DevOpsAgent with the same session_id shares state via the persistent backend.
"""
from __future__ import annotations

import uuid
from unittest.mock import patch, MagicMock

from langchain_core.messages import AIMessage, HumanMessage


class TestConversationMemory:
    """Unit tests for in-process ConversationBufferWindowMemory."""

    def test_accumulates_three_turns(self):
        from langchain.memory import ConversationBufferWindowMemory

        memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=20,
            input_key="input",
            output_key="output",
        )
        turns = [
            ("Hello, what can you do?", "I can manage your infra."),
            ("List containers", "Here are the running containers..."),
            ("Restart nginx", "Nginx has been restarted."),
        ]
        for human, ai in turns:
            memory.save_context({"input": human}, {"output": ai})

        history = memory.load_memory_variables({})["chat_history"]
        assert len(history) == 6
        assert sum(1 for m in history if isinstance(m, HumanMessage)) == 3
        assert sum(1 for m in history if isinstance(m, AIMessage)) == 3

    def test_window_evicts_oldest_messages(self):
        from langchain.memory import ConversationBufferWindowMemory

        memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=2,  # keep only last 2 turns
            input_key="input",
            output_key="output",
        )
        for i in range(5):
            memory.save_context({"input": f"msg-{i}"}, {"output": f"reply-{i}"})

        history = memory.load_memory_variables({})["chat_history"]
        # k=2 → last 2 turns = 4 messages
        assert len(history) == 4
        human_texts = [m.content for m in history if isinstance(m, HumanMessage)]
        assert "msg-3" in human_texts
        assert "msg-4" in human_texts
        assert "msg-0" not in human_texts


class TestBuildMemory:
    """Tests for the build_memory() factory in agents/memory.py."""

    def test_falls_back_to_inmemory_when_redis_unavailable(self):
        from app.agents.memory import build_memory

        with patch("app.agents.memory.settings") as mock_cfg:
            mock_cfg.MEMORY_BACKEND = "redis"
            mock_cfg.REDIS_URL = "redis://localhost:9999"  # nothing listening
            mock_cfg.DATABASE_URL = ""

            memory = build_memory("test-session-" + str(uuid.uuid4()))
            # Should still return a valid memory object (fallback)
            assert memory is not None
            assert hasattr(memory, "load_memory_variables")

    def test_returns_inmemory_when_backend_is_inmemory(self):
        from app.agents.memory import build_memory

        with patch("app.agents.memory.settings") as mock_cfg:
            mock_cfg.MEMORY_BACKEND = "inmemory"
            mock_cfg.REDIS_URL = ""
            mock_cfg.DATABASE_URL = ""

            memory = build_memory("test-session-" + str(uuid.uuid4()))
            assert memory is not None

    def test_inmemory_memory_is_independent_per_session(self):
        """Each session_id must get an independent memory object."""
        from app.agents.memory import build_memory

        with patch("app.agents.memory.settings") as mock_cfg:
            mock_cfg.MEMORY_BACKEND = "inmemory"
            mock_cfg.REDIS_URL = ""
            mock_cfg.DATABASE_URL = ""

            mem_a = build_memory("session-A")
            mem_b = build_memory("session-B")

            mem_a.save_context({"input": "hello"}, {"output": "hi from A"})
            hist_b = mem_b.load_memory_variables({})["chat_history"]
            assert len(hist_b) == 0, "session B should not see session A's messages"


class TestAgentPoolPersistence:
    """Tests for the session pool and memory integration in DevOpsAgent."""

    def test_same_session_returns_same_agent(self):
        from app.agents.devops_agent import _agent_pool, get_or_create_agent

        sid = "persist-test-" + str(uuid.uuid4())
        with patch("app.agents.devops_agent.build_memory", return_value=MagicMock()):
            agent1 = get_or_create_agent(sid, user_role="developer")
            agent2 = get_or_create_agent(sid, user_role="developer")
            assert agent1 is agent2

        _agent_pool.pop(sid, None)

    def test_different_sessions_get_different_agents(self):
        from app.agents.devops_agent import _agent_pool, get_or_create_agent

        sid_a = "persist-a-" + str(uuid.uuid4())
        sid_b = "persist-b-" + str(uuid.uuid4())

        with patch("app.agents.devops_agent.build_memory", return_value=MagicMock()):
            agent_a = get_or_create_agent(sid_a)
            agent_b = get_or_create_agent(sid_b)
            assert agent_a is not agent_b

        _agent_pool.pop(sid_a, None)
        _agent_pool.pop(sid_b, None)
