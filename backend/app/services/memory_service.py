"""
Persistent conversation memory backed by the database.

Replaces the in-process ConversationBufferWindowMemory so sessions
survive server restarts and work across multiple worker processes.

Usage
-----
    history = DBChatMessageHistory(session_id="abc", db=session)
    memory  = build_memory(history)
    # pass `memory` to AgentExecutor(memory=memory, ...)
"""
from __future__ import annotations

from typing import Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain.memory import ConversationBufferWindowMemory
from langchain_community.chat_message_histories.in_memory import ChatMessageHistory
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import ChatMessage

# Window size — how many messages to load into the prompt
MEMORY_WINDOW_K = 20


class DBChatMessageHistory:
    """
    Async-capable chat history store backed by the ``chat_messages`` table.
    Implements the minimal interface LangChain needs from a message history.
    """

    def __init__(self, session_id: str, db: AsyncSession) -> None:
        self.session_id = session_id
        self._db = db

    # ── Read ──────────────────────────────────────────────────────────────────

    async def aget_messages(self, limit: int = MEMORY_WINDOW_K) -> list[BaseMessage]:
        """Return the last *limit* messages, oldest first."""
        result = await self._db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == self.session_id)
            .order_by(ChatMessage.id.desc())
            .limit(limit)
        )
        rows: Sequence[ChatMessage] = result.scalars().all()
        messages: list[BaseMessage] = []
        for row in reversed(rows):
            if row.role == "human":
                messages.append(HumanMessage(content=row.content))
            else:
                messages.append(AIMessage(content=row.content))
        return messages

    # ── Write ─────────────────────────────────────────────────────────────────

    async def aadd_messages(self, human_text: str, ai_text: str) -> None:
        """Persist one conversational turn (human + AI)."""
        self._db.add(ChatMessage(session_id=self.session_id, role="human", content=human_text))
        self._db.add(ChatMessage(session_id=self.session_id, role="ai",    content=ai_text))
        await self._db.flush()

    # ── Clear ─────────────────────────────────────────────────────────────────

    async def aclear(self) -> None:
        """Delete all messages for this session."""
        await self._db.execute(
            delete(ChatMessage).where(ChatMessage.session_id == self.session_id)
        )
        await self._db.flush()


def build_in_memory_window(messages: list[BaseMessage]) -> ConversationBufferWindowMemory:
    """
    Construct a ConversationBufferWindowMemory pre-loaded with *messages*.

    This is called once per request: we load history from the DB,
    stuff it into an in-memory buffer, pass that to the AgentExecutor,
    then save the new turn back to the DB after the call returns.
    """
    chat_history = ChatMessageHistory(messages=messages)
    memory = ConversationBufferWindowMemory(
        chat_memory=chat_history,
        memory_key="chat_history",
        return_messages=True,
        k=MEMORY_WINDOW_K,
        input_key="input",
        output_key="output",
    )
    return memory
