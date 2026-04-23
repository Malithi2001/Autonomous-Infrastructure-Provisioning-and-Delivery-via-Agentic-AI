# System Architecture

## Overview

The Smart DevOps Assistant is a modular, full-stack system built on four main layers:

1. **Frontend** — React/Vite dashboard (chat UI, HITL approvals, execution logs)
2. **Backend** — FastAPI REST API (auth, RBAC, request routing, audit logging)
3. **Agent Core** — LangChain-powered AI brain (planning, reasoning, tool dispatch)
4. **Target Infrastructure** — Docker, GitHub Actions, AWS EC2 sandbox environment

---

## Layer Detail

### 1. Frontend (React 18 + Vite + Tailwind)

```
src/
├── pages/
│   ├── ChatPage.tsx        # Main chat interface with streaming messages
│   ├── ApprovalsPage.tsx   # HITL approval queue for operators
│   ├── ExecutionsPage.tsx  # Audit log / execution history
│   └── LoginPage.tsx       # JWT authentication
├── store/
│   ├── authStore.ts        # Zustand auth state (persisted)
│   └── chatStore.ts        # Conversation messages & session state
├── services/
│   └── api.ts              # Axios-based API layer with token injection
└── components/
    └── layout/Layout.tsx   # Sidebar navigation
```

### 2. Backend (FastAPI + SQLAlchemy + Async PostgreSQL)

```
app/
├── api/routes/
│   ├── agent.py        # POST /api/v1/agent/chat — main entry point
│   ├── auth.py         # POST /api/v1/auth/login|register
│   ├── approvals.py    # GET/POST /api/v1/approvals — HITL gate
│   ├── executions.py   # GET /api/v1/executions — audit trail
│   ├── webhooks.py     # POST /api/v1/webhooks/github — CI/CD events
│   └── health.py       # GET /health
├── core/
│   ├── config.py       # Pydantic Settings (env vars)
│   ├── database.py     # Async SQLAlchemy engine + session
│   ├── security.py     # JWT, bcrypt, RBAC permission matrix
│   └── logging.py      # Structured JSON logging (structlog)
├── models/models.py    # DB schema: User, Execution, ApprovalRequest, AuditLog
└── schemas/schemas.py  # Pydantic I/O validation schemas
```

### 3. Agent Core (LangChain)

```
agents/
├── devops_agent.py     # AgentExecutor builder, session pool, chat() method
└── tools_registry.py  # Role-filtered tool list builder

tools/
├── docker_tool.py      # Docker SDK integration (list, logs, restart, run)
├── github_tool.py      # PyGithub integration (workflows, runs, dispatch)
├── shell_tool.py       # Allowlisted shell commands only
└── monitoring_tool.py  # psutil metrics + HTTP health checks
```

### 4. Data Flow

```
User types message
       ↓
[Frontend ChatPage]
       ↓  POST /api/v1/agent/chat
[FastAPI backend]
  → JWT validated
  → RBAC permission check (agent:chat)
  → Execution record created (status: pending)
       ↓
[LangChain AgentExecutor]
  → LLM reads system prompt + conversation history
  → LLM generates action plan
  → Checks risk level of action
       ↓
  If HIGH/CRITICAL risk:
    → Creates ApprovalRequest in DB
    → Returns "requires_approval: true" to frontend
    → Frontend shows approval banner
    → Operator approves/rejects via ApprovalsPage
  If LOW/MEDIUM risk:
    → Calls appropriate tool (Docker/GitHub/Shell/Monitor)
    → Tool executes real action
    → Result returned to LLM
    → LLM summarizes result for user
       ↓
[Execution record updated: status, result, completed_at]
[AuditLog entry created]
       ↓
Response streamed back to frontend
```

---

## Security Architecture

### RBAC Permission Matrix

| Permission | Viewer | Developer | Operator | Admin |
|------------|--------|-----------|----------|-------|
| logs:read | ✅ | ✅ | ✅ | ✅ |
| agent:chat | ❌ | ✅ | ✅ | ✅ |
| deployments:staging | ❌ | ✅ | ✅ | ✅ |
| deployments:production | ❌ | ❌ | ✅ | ✅ |
| infrastructure:write | ❌ | ❌ | ✅ | ✅ |
| * (all) | ❌ | ❌ | ❌ | ✅ |

### HITL (Human-in-the-Loop) Flow

```
Agent identifies HIGH risk action
         ↓
Creates ApprovalRequest (status: pending, expires: +5min)
         ↓
Execution paused → frontend notified
         ↓
Operator sees alert in ApprovalsPage
         ↓
    APPROVE → execution resumes
    REJECT  → execution cancelled, user notified
    TIMEOUT → execution auto-cancelled
```

---

## Database Schema (ERD Summary)

```
users               executions              approval_requests
─────────────       ──────────────────      ─────────────────────
id (UUID PK)        id (UUID PK)            id (UUID PK)
email               user_id (FK→users)      execution_id (FK)
username            session_id              requested_by_id (FK)
hashed_password     command                 approved_by_id (FK)
role (enum)         action_plan (JSON)      description
is_active           tool_used               status (enum)
created_at          result                  expires_at
                    status (enum)           decided_at
                    risk_level              decision_note
                    created_at              created_at
                    completed_at

audit_logs
──────────────────
id (int PK)
user_id
event_type
event_data (JSON)
ip_address
timestamp
```

---

## Technology Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| AI Framework | LangChain | Mature, production-ready, tools + memory support |
| LLM | GPT-4o / Claude | Strongest instruction-following for DevOps tasks |
| API | FastAPI | Async-native, auto OpenAPI docs, Pydantic integration |
| DB | PostgreSQL | ACID compliance critical for audit logs |
| Frontend | React + Vite | Fast HMR, TypeScript, strong ecosystem |
| State | Zustand | Minimal, no boilerplate, persisted auth |
| Containers | Docker + Compose | Portable, reproducible environments |
