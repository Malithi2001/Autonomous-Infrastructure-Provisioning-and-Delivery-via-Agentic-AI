"""
LangChain Agent Core
The "Brain" of the DevOps Assistant — handles intent recognition,
action planning, tool dispatch, and conversational memory.
"""
import asyncio
from typing import AsyncGenerator, Optional

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

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


class DevOpsAgent:
    """Core LangChain agent for DevOps task execution."""

    def __init__(self, session_id: str, user_role: str = "developer"):
        self.session_id = session_id
        self.user_role = user_role
        self._executor: Optional[AgentExecutor] = None

    def _build_executor(self) -> AgentExecutor:
        """Build and return the LangChain AgentExecutor."""
        llm = ChatOpenAI(
            model=settings.DEFAULT_MODEL,
            temperature=0,
            streaming=True,
            openai_api_key=settings.OPENAI_API_KEY,
        )

        tools = get_all_tools(user_role=self.user_role)

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ])

        memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=20,  # Keep last 20 messages
        )

        agent = create_openai_tools_agent(llm, tools, prompt)

        return AgentExecutor(
            agent=agent,
            tools=tools,
            memory=memory,
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
        """Process a user message and return the agent response."""
        from datetime import datetime
        try:
            logger.info("agent.chat", session_id=self.session_id, message=user_message[:100])
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.executor.invoke({
                    "input": user_message,
                    "current_datetime": datetime.utcnow().isoformat(),
                })
            )
            return {
                "output": result.get("output", ""),
                "intermediate_steps": result.get("intermediate_steps", []),
                "session_id": self.session_id,
            }
        except Exception as e:
            logger.error("agent.chat.error", error=str(e), session_id=self.session_id)
            raise


# Session-based agent pool (in production, use Redis for distributed sessions)
_agent_pool: dict[str, DevOpsAgent] = {}


def get_or_create_agent(session_id: str, user_role: str = "developer") -> DevOpsAgent:
    """Get existing agent for a session or create a new one."""
    if session_id not in _agent_pool:
        _agent_pool[session_id] = DevOpsAgent(session_id=session_id, user_role=user_role)
    return _agent_pool[session_id]
