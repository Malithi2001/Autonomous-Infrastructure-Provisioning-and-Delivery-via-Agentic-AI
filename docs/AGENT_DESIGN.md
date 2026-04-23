# Agent Design

## Overview

The AI brain is a **LangChain ReAct agent** powered by GPT-4o (or Claude). It receives natural language DevOps commands, reasons through a plan, selects appropriate tools, executes them, and returns a human-readable summary.

---

## Agent Architecture

```
User Input (NL command)
        ↓
System Prompt + Conversation Memory
        ↓
LLM (GPT-4o / Claude)
        ↓ Generates a plan
Tool Selection
        ↓
Tool Execution (Docker / GitHub / Shell / Monitor)
        ↓
Result → LLM interprets result
        ↓
Risk Classification
        ↓
HITL Gate (if HIGH/CRITICAL) or Direct Response
        ↓
Structured Summary → User
```

---

## System Prompt Design

The agent is given a detailed system prompt that defines:

1. **Role** — "You are a virtual DevOps engineer"
2. **Responsibilities** — translate NL to infrastructure actions
3. **Safety rules** — never execute high-risk actions without approval
4. **Response format** — Understanding → Plan → Risk → Execution → Summary

This structured prompt design ensures the agent is predictable, auditable, and safe.

---

## Available Tools

### Read-Only Tools (All roles)

| Tool | Description |
|------|-------------|
| `docker_list_containers` | Lists all Docker containers with status and ports |
| `docker_get_logs` | Fetches container logs with timestamps |
| `get_system_metrics` | CPU, memory, disk, and network stats via psutil |
| `get_service_health` | HTTP health check on any endpoint |
| `github_list_workflows` | Lists all GitHub Actions workflows |
| `github_workflow_status` | Status of a specific workflow run |
| `github_recent_runs` | Last N workflow runs with conclusions |

### Elevated Tools (Operator / Admin only)

| Tool | Risk | Description |
|------|------|-------------|
| `docker_restart_container` | Medium | Restarts a container (self-healing) |
| `docker_start_container` | Medium | Starts a stopped container |
| `docker_stop_container` | High | Stops a running container |
| `docker_run_container` | High | Runs a new container from an image |
| `github_trigger_workflow` | High | Triggers a CI/CD workflow dispatch |
| `execute_shell_command` | Medium | Runs pre-approved shell commands only |

---

## Memory System

The agent uses `ConversationBufferWindowMemory` with a window of 20 messages. This means:
- The agent remembers the last 20 user/assistant turns per session
- Conversation context is preserved: "restart **that** container" works after "list containers"
- Sessions are isolated per user session ID
- Memory is currently in-process (for production, migrate to Redis-backed memory)

---

## Risk Classification

The agent must classify every action before executing it:

| Risk | Criteria | Example |
|------|----------|---------|
| Low | Read-only, no side effects | `docker_list_containers`, `get_system_metrics` |
| Medium | Reversible write operations | Container restart, health check trigger |
| High | Significant or partially irreversible changes | Production deploy, container stop |
| Critical | Destructive, hard to reverse | Data deletion, cluster teardown |

For `HIGH` and `CRITICAL` actions, the agent pauses and creates a `ApprovalRequest` before proceeding.

---

## Self-Healing Workflow

When a GitHub webhook fires a `workflow_run: failure` event:

1. Webhook handler receives the event
2. Agent is triggered automatically with context: `"CI pipeline failed for repo X, workflow Y"`
3. Agent fetches workflow logs using `github_workflow_status`
4. Agent parses error patterns
5. Agent proposes remediation (e.g., restart affected service, rollback deployment)
6. If remediation is medium risk → auto-executes
7. If high risk → creates HITL approval request → notifies operator

---

## Session Management

```python
# Each user gets an isolated agent session
agent = get_or_create_agent(session_id="user-123-session-abc", user_role="operator")
result = await agent.chat("Restart the payment service container")
```

Sessions are pooled in memory per process. For multi-worker/distributed deployments, sessions should be serialized to Redis.

---

## Extending with New Tools

To add a new DevOps tool:

1. Create `backend/app/tools/your_tool.py` with tool functions
2. Register in `backend/app/agents/tools_registry.py`:
```python
from app.tools.your_tool import your_function

StructuredTool.from_function(
    func=your_function,
    name="your_tool_name",
    description="Clear description of what the tool does and when to use it.",
)
```
3. Add to appropriate role tier in `get_all_tools()`
4. Write tests in `backend/tests/`

The agent will automatically discover and use the new tool based on its description.
