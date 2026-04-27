"""
LangChain Agent Core — the "Brain" of the DevOps Assistant.

Supports: OpenAI GPT-4o  |  Anthropic Claude  |  Ollama (local)
Memory:   Redis (prod)   |  PostgreSQL        |  in-process (dev)
"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Optional

from langchain.agents import AgentExecutor, create_openai_tools_agent, create_structured_chat_agent
from langchain_community.chat_models import ChatOllama
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import LLMResult
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from app.agents.memory import build_memory
from app.agents.tools_registry import get_all_tools
from app.core.config import settings
from app.core.logging import logger

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

Use this exact format:

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
    """Collects streamed tokens into an asyncio.Queue for WebSocket delivery."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[str | None] = asyncio.Queue()

    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        await self._queue.put(token)

    async def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        await self._queue.put(None)

    async def on_llm_error(self, error: BaseException, **kwargs) -> None:
        await self._queue.put(None)

    async def token_stream(self) -> AsyncIterator[str]:
        while True:
            token = await self._queue.get()
            if token is None:
                break
            yield token


class InMemoryTestExecutor:
    """Tiny test executor that exercises the same memory object without external APIs."""

    def __init__(self, memory: Any) -> None:
        self.memory = memory

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        user_message = inputs["input"]
        history = self.memory.load_memory_variables({}).get("chat_history", [])
        human_messages = [msg.content for msg in history if isinstance(msg, HumanMessage)]
        ai_messages = [msg.content for msg in history if isinstance(msg, AIMessage)]

        if len(human_messages) >= 2 and "first message" in user_message.lower():
            output = f"Your first message was: {human_messages[0]}"
        elif human_messages:
            output = (
                f"Remembered {len(human_messages)} prior user messages. "
                f"Latest was: {human_messages[-1]}"
            )
        elif ai_messages:
            output = f"Previous assistant reply: {ai_messages[-1]}"
        else:
            output = f"Test agent received: {user_message}"

        self.memory.save_context({"input": user_message}, {"output": output})
        return {"output": output, "intermediate_steps": []}


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
        )

    if provider == "openai":
        return ChatOpenAI(
            model=settings.DEFAULT_MODEL or "gpt-4o",
            temperature=0,
            streaming=streaming,
            openai_api_key=settings.OPENAI_API_KEY,
            callbacks=cb,
        )

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


# ── Core agent class ──────────────────────────────────────────────────────────

class DevOpsAgent:
    """
    Session-scoped LangChain agent with persistent memory.

    Memory is backed by Redis or Postgres (see agents/memory.py).
    Falls back to in-process ConversationBufferWindowMemory in dev.
    """

    def __init__(self, session_id: str, user_role: str = "developer") -> None:
        self.session_id = session_id
        self.user_role = user_role
        self._executor: Optional[AgentExecutor] = None
        # Build once; the underlying store is the persistent backend
        self._memory = build_memory(session_id)

    def _build_executor(self, callbacks: list | None = None) -> AgentExecutor:
        provider = settings.DEFAULT_LLM_PROVIDER.lower()
        if provider == "test":
            return InMemoryTestExecutor(self._memory)

        llm = _build_llm(streaming=bool(callbacks), callbacks=callbacks)
        tools = get_all_tools(user_role=self.user_role)
        prompt = _build_prompt(provider)

        if provider in ("openai", "anthropic"):
            agent = create_openai_tools_agent(llm, tools, prompt)
        else:
            agent = create_structured_chat_agent(llm, tools, prompt, stop_sequence=False)

        return AgentExecutor(
            agent=agent,
            tools=tools,
            memory=self._memory,
            verbose=settings.DEBUG,
            max_iterations=settings.AGENT_MAX_ITERATIONS,
            handle_parsing_errors=True,
            return_intermediate_steps=True,
        )

    @property
    def executor(self) -> AgentExecutor:
        if self._executor is None:
            self._executor = self._build_executor()
        return self._executor

    async def chat(self, user_message: str) -> dict:
        """Process a message and return the full agent response (non-streaming)."""
        from datetime import datetime, timezone
        try:
            logger.info("agent.chat", session_id=self.session_id, message=user_message[:100])
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.executor.invoke({
                    "input": user_message,
                    "current_datetime": datetime.now(tz=timezone.utc).isoformat(),
                }),
            )
            return {
                "output": result.get("output", ""),
                "intermediate_steps": result.get("intermediate_steps", []),
                "session_id": self.session_id,
            }
        except Exception as exc:
            logger.error("agent.chat.error", error=str(exc), session_id=self.session_id)
            raise

    async def stream_chat(self, user_message: str) -> AsyncIterator[str]:
        """Process a message and yield individual tokens as they are generated."""
        from datetime import datetime, timezone
        callback = TokenStreamCallback()
        executor = self._build_executor(callbacks=[callback])

        if settings.DEFAULT_LLM_PROVIDER.lower() == "test":
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: executor.invoke({"input": user_message}),
            )
            for chunk in result.get("output", ""):
                yield chunk
            return

        async def _run() -> None:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: executor.invoke({
                    "input": user_message,
                    "current_datetime": datetime.now(tz=timezone.utc).isoformat(),
                }),
            )

        task = asyncio.create_task(_run())
        async for token in callback.token_stream():
            yield token
        await task


# ── Session pool ──────────────────────────────────────────────────────────────

# The in-process dict maps session_id → agent object.
# With persistent memory backends (Redis/Postgres), re-creating the agent
# on a new worker process is safe: history is reloaded from the store.
_agent_pool: dict[str, DevOpsAgent] = {}


def get_or_create_agent(session_id: str, user_role: str = "developer") -> DevOpsAgent:
    """Return an existing agent for the session or create a fresh one."""
    if session_id not in _agent_pool:
        _agent_pool[session_id] = DevOpsAgent(session_id=session_id, user_role=user_role)
        logger.info("agent.session.created", session_id=session_id, user_role=user_role)
    return _agent_pool[session_id]
