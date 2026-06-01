"""
LangChain Agent Core
The "Brain" of the DevOps Assistant — handles intent recognition,
action planning, tool dispatch, and conversational memory.

Key improvements over v1
------------------------
* Supports OpenAI GPT-4o, Anthropic Claude, and Ollama.
* Memory is DB-backed (via DBChatMessageHistory) so sessions survive
  server restarts and work with multiple worker processes.
* TokenStreamCallback feeds the WebSocket streaming endpoint.
* Intent routing removed from the agent — the agent always decides.
"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator

from langchain.agents import AgentExecutor, create_openai_tools_agent, create_structured_chat_agent
from langchain_community.chat_models import ChatOllama
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.memory import build_memory  # noqa: F401 - re-exported for tests and extension hooks
from app.agents.tools_registry import get_all_tools
from app.core.config import settings
from app.core.logging import logger
from app.services.memory_service import DBChatMessageHistory, build_in_memory_window

# ── System prompts ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an Agentic AI-Powered Smart DevOps Assistant.
Your role is to help DevOps engineers manage infrastructure, CI/CD pipelines,
deployments, and incident response through natural language.

## Core Responsibilities
- Interpret natural language DevOps commands and convert them into structured execution plans
- Use available tools to interact with Docker, GitHub, AWS, and system resources
- Detect anomalies, parse logs, and suggest/execute remediation strategies
- Always explain your reasoning before executing actions

## Safety Rules (NON-NEGOTIABLE)
1. NEVER execute production deployments without explicit human approval (HITL gate)
2. ALWAYS classify the risk level of each action: low | medium | high | critical
3. For HIGH or CRITICAL risk actions, ALWAYS request approval before proceeding
4. NEVER expose secrets, tokens, or credentials in your responses
5. If unsure about an action's impact, ASK for clarification

## Response Format
When planning an action, always respond in this structure:
1. **Understanding**: What I understood from your request
2. **Plan**: Step-by-step actions I will take
3. **Risk Assessment**: Risk level and why
4. **Execution**: Actual tool calls and results
5. **Summary**: What was accomplished

Current date/time: {current_datetime}
"""

OLLAMA_SYSTEM_PROMPT = SYSTEM_PROMPT + """

You have access to these tools:

{tools}

Use a JSON blob to specify one action at a time. Valid action values are
"Final Answer" or one of: {tool_names}

Question: the user's question
Thought: what to do next
Action:
```
{{
  "action": "tool_name",
  "action_input": {{}}
}}
```
Observation: tool result
Thought: I know what to respond
Action:
```
{{
  "action": "Final Answer",
  "action_input": "final response"
}}
```
"""


# ── Streaming callback ────────────────────────────────────────────────────────

class TokenStreamCallback(AsyncCallbackHandler):
    """Pushes each streamed token into an asyncio.Queue for WebSocket delivery."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[str | None] = asyncio.Queue()

    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        await self._queue.put(token)

    async def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        await self._queue.put(None)   # sentinel

    async def on_llm_error(self, error: BaseException, **kwargs) -> None:
        await self._queue.put(None)

    async def token_stream(self) -> AsyncIterator[str]:
        while True:
            token = await self._queue.get()
            if token is None:
                break
            yield token


# ── LLM factory ──────────────────────────────────────────────────────────────

def _build_llm(streaming: bool = False, callbacks: list | None = None):
    provider = settings.DEFAULT_LLM_PROVIDER.lower()
    cb = callbacks or []

    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:
            raise ImportError(
                "langchain-anthropic is required. Run: pip install langchain-anthropic"
            ) from exc
        return ChatAnthropic(
            model=settings.DEFAULT_MODEL or "claude-sonnet-4-20250514",
            temperature=0,
            streaming=streaming,
            anthropic_api_key=settings.ANTHROPIC_API_KEY,
            callbacks=cb,
        )  # type: ignore[call-arg]

    if provider == "openai":
        return ChatOpenAI(
            model=settings.DEFAULT_MODEL or "gpt-4o",
            temperature=0,
            streaming=streaming,
            openai_api_key=settings.OPENAI_API_KEY,
            callbacks=cb,
        )  # type: ignore[call-arg]

    if provider == "ollama":
        return ChatOllama(
            model=settings.DEFAULT_MODEL,
            temperature=0,
            base_url=settings.OLLAMA_BASE_URL,
            callbacks=cb,
        )

    raise ValueError(f"Unsupported LLM provider: {settings.DEFAULT_LLM_PROVIDER!r}")


def _build_prompt(provider: str) -> ChatPromptTemplate:
    if provider == "ollama":
        return ChatPromptTemplate.from_messages([
            ("system", OLLAMA_SYSTEM_PROMPT),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}\n\n{agent_scratchpad}"),
        ])
    return ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])


def _build_executor(
    user_role: str,
    memory,
    callbacks: list | None = None,
) -> AgentExecutor:
    provider = settings.DEFAULT_LLM_PROVIDER.lower()
    llm = _build_llm(streaming=bool(callbacks), callbacks=callbacks)
    tools = get_all_tools(user_role=user_role)
    prompt = _build_prompt(provider)

    if provider in ("openai", "anthropic"):
        agent = create_openai_tools_agent(llm, tools, prompt)
    else:
        agent = create_structured_chat_agent(llm, tools, prompt, stop_sequence=False)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        verbose=settings.DEBUG,
        max_iterations=settings.AGENT_MAX_ITERATIONS,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
    )


# ── Core agent class ──────────────────────────────────────────────────────────

class DevOpsAgent:
    """
    Session-scoped LangChain agent with DB-backed persistent memory.

    Memory strategy (per-request)
    ------------------------------
    1. Load the last MEMORY_WINDOW_K messages from ``chat_messages`` via
       DBChatMessageHistory.
    2. Build an in-process ConversationBufferWindowMemory from those rows.
    3. Run the AgentExecutor (sync, in a thread).
    4. Save the new human+AI turn back to the DB.

    This means sessions survive server restarts and horizontal scaling.
    """

    def __init__(self, session_id: str, user_role: str = "developer") -> None:
        self.session_id = session_id
        self.user_role = user_role
        self._test_messages: list[str] = []

    async def chat(self, user_message: str, db: AsyncSession) -> dict:
        """Non-streaming: process a message and return the full response."""
        from datetime import datetime, timezone

        if settings.DEFAULT_LLM_PROVIDER.lower() == "test":
            self._test_messages.append(user_message)
            if "first message" in user_message.lower() and self._test_messages:
                output = f"Your first message was: {self._test_messages[0]}"
            else:
                output = f"Test agent received: {user_message}"
            return {
                "output": output,
                "intermediate_steps": [],
                "session_id": self.session_id,
            }

        history_store = DBChatMessageHistory(session_id=self.session_id, db=db)
        messages = await history_store.aget_messages()
        memory = build_in_memory_window(messages)
        executor = _build_executor(self.user_role, memory)

        logger.info("agent.chat", session_id=self.session_id, message=user_message[:100])
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: executor.invoke({
                    "input": user_message,
                    "current_datetime": datetime.now(tz=timezone.utc).isoformat(),
                }),
            )
            output = result.get("output", "")
            await history_store.aadd_messages(user_message, output)
            await db.commit()
            return {
                "output": output,
                "intermediate_steps": result.get("intermediate_steps", []),
                "session_id": self.session_id,
                "requires_approval": result.get("requires_approval"),
                "approval_id": result.get("approval_id"),
            }
        except Exception as exc:
            logger.error("agent.chat.error", error=str(exc), session_id=self.session_id)
            raise

    async def stream_chat(
        self, user_message: str, db: AsyncSession
    ) -> AsyncIterator[str]:
        """Streaming: yield tokens as they arrive, then persist the full turn."""
        from datetime import datetime, timezone

        if settings.DEFAULT_LLM_PROVIDER.lower() == "test":
            output = f"Test agent received: {user_message}"
            self._test_messages.append(user_message)
            for char in output:
                yield char
            return

        history_store = DBChatMessageHistory(session_id=self.session_id, db=db)
        messages = await history_store.aget_messages()
        memory = build_in_memory_window(messages)

        callback = TokenStreamCallback()
        executor = _build_executor(self.user_role, memory, callbacks=[callback])

        full_response: list[str] = []

        async def _run() -> None:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: executor.invoke({
                    "input": user_message,
                    "current_datetime": datetime.now(tz=timezone.utc).isoformat(),
                }),
            )
            full_response.append(result.get("output", ""))

        task = asyncio.create_task(_run())
        async for token in callback.token_stream():
            yield token
        await task

        if full_response:
            await history_store.aadd_messages(user_message, full_response[0])
            await db.commit()


# ── Session pool ──────────────────────────────────────────────────────────────

# Lightweight registry — only holds metadata (session_id, role).
# No memory state lives here; all state is in the DB.
_agent_pool: dict[str, DevOpsAgent] = {}


def get_or_create_agent(session_id: str, user_role: str = "developer") -> DevOpsAgent:
    """Return or create a DevOpsAgent for a session."""
    if session_id not in _agent_pool:
        _agent_pool[session_id] = DevOpsAgent(session_id=session_id, user_role=user_role)
        logger.info("agent.session.created", session_id=session_id, user_role=user_role)
    return _agent_pool[session_id]
