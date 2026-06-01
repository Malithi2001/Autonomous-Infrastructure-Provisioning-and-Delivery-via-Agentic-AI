# System Architecture

## Overview

The Smart DevOps Assistant is a modular, full-stack system built on four main layers:

1. **Frontend** — React/Vite dashboard (chat UI, multi-agent demo, CI/CD assistant, HITL approvals, audit logs)
2. **Backend** — FastAPI REST API (auth, RBAC, deterministic agent routing, audit logging)
3. **Agent Core** — Orchestration Agent plus specialized agents for CLI, CI/CD, diagnosis, and GitHub workflows
4. **Tools and Services** — Docker, repository analyzer, workflow generator, ML prediction, GitHub REST API

---

## Layer Detail

### 1. Frontend (React 18 + Vite + Tailwind)

```
src/
├── pages/
│   ├── ChatPage.tsx        # Main chat interface with streaming messages
│   ├── MultiAgentPage.tsx  # Supervisor demo for orchestration and specialized agents
│   ├── DiagnosisPage.tsx   # CI/CD failure prediction and workflow generation
│   ├── RepositorySetupPage.tsx # Repository scan and workflow PR flow
│   ├── WorkflowFailuresPage.tsx # Stored GitHub Actions failure diagnosis
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
│   ├── agent.py        # POST /api/v1/agent/chat and /api/v1/agent/orchestrate
│   ├── auth.py         # POST /api/v1/auth/login|register
│   ├── cicd.py         # Repository file analysis and workflow YAML generation
│   ├── repositories.py # GitHub repository scan and workflow PR APIs
│   ├── workflow_failures.py # Persisted failure diagnosis and fix PR API
│   ├── approvals.py    # GET/POST /api/v1/approvals — HITL gate
│   ├── executions.py   # GET /api/v1/audit and execution detail APIs
│   ├── webhooks.py     # POST /api/v1/webhooks/github — CI/CD events
│   └── health.py       # GET /health
├── core/
│   ├── config.py       # Pydantic Settings (env vars)
│   ├── database.py     # Async SQLAlchemy engine + session
│   ├── security.py     # JWT, bcrypt, RBAC permission matrix
│   └── logging.py      # Structured JSON logging (structlog)
├── models/models.py    # DB schema: User, Execution, ApprovalRequest, WorkflowFailure, RepositoryInstallation
└── schemas/schemas.py  # Pydantic I/O validation schemas
```

### 3. Agent Core

```
agents/
├── agent_types.py          # AgentTask and AgentResult shared Pydantic models
├── orchestration_agent.py  # Deterministic router for specialized agents
├── cli_agent.py            # Docker/container operations through Docker tool
├── cicd_agent.py           # Repo analysis and workflow YAML generation
├── diagnosis_agent.py      # ML failure prediction and fix recommendation
├── github_agent.py         # GitHub scan, workflow PR, workflow trigger, fix PR
├── devops_agent.py         # Existing chat agent/session pool
└── tools_registry.py       # Role-filtered tool list builder

tools/
├── docker_tool.py      # Docker SDK integration (list, logs, restart, run)
├── github_tool.py      # GitHub REST integration (repo tree, logs, workflows, branches, files, PRs)
├── shell_tool.py       # Allowlisted shell commands only
└── monitoring_tool.py  # psutil metrics + HTTP health checks
```

### 4. Multi-Agent Architecture

The supervisor-required multi-agent path is deterministic and easy to test:

```text
User
  -> Orchestration Agent
  -> Specialized Agent
  -> Tool/Service Call
  -> Result
  -> Audit Log / Approval if needed
```

The API entry point is:

```text
POST /api/v1/agent/orchestrate
```

Agent responsibilities:

| Agent | Responsibility | Example request | Tool/service |
| --- | --- | --- | --- |
| Orchestration Agent | Detects intent and selects one specialized agent | `show running containers` | Specialized agent router |
| CLI Agent | Safe Docker/container operations | `docker ps` | `docker_tool.list_containers` |
| CI/CD Agent | File-list stack detection and local workflow generation | `generate CI workflow for React project` | `repo_analyzer`, `workflow_generator` |
| Diagnosis Agent | CI/CD log classification and fix recommendation | `analyze this log` | `failure_prediction_service`, `fix_recommendation_service` |
| GitHub Agent | GitHub repo scan, workflow PR, workflow trigger, fix PR | `scan repository owner/repo` | `github_tool`, `fix_pr_service` |

Routing examples:

```text
show running containers
  -> cli_agent
  -> docker_list_containers
  -> low risk
```

```text
generate CI workflow for React project
  -> cicd_agent
  -> cicd_generate_workflow
  -> low risk
```

```text
analyze this log: npm ERR! Missing script test
  -> diagnosis_agent
  -> cicd_failure_diagnosis
  -> low risk
```

```text
scan repository owner/repo
  -> github_agent
  -> github_scan_repository
  -> low risk
```

```text
create workflow PR
  -> github_agent
  -> github_create_workflow_pr
  -> medium risk
  -> pending approval before execution
```

### 5. Chat Agent Data Flow

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

### 6. CI/CD Automation Data Flow

```text
GitHub workflow_run webhook
       ↓
FastAPI webhook route
       ↓
Download GitHub Actions logs
       ↓
Clean, truncate, and redact logs
       ↓
Failure prediction model
       ↓
Fix recommendation service
       ↓
WorkflowFailure record
       ↓
Audit log entry
       ↓
Frontend Workflow Failures page
```

---

## Security Architecture

### RBAC Permission Matrix

| Permission | Viewer | Developer | Operator | Admin |
|------------|--------|-----------|----------|-------|
| logs:read | ✅ | ✅ | ✅ | ✅ |
| agent:chat | ✅ | ✅ | ✅ | ✅ |
| deployments:staging | ❌ | ✅ | ✅ | ✅ |
| deployments:production | ❌ | ❌ | ✅ | ✅ |
| infrastructure:write | ❌ | ❌ | ✅ | ✅ |
| * (all) | ❌ | ❌ | ❌ | ✅ |

### HITL (Human-in-the-Loop) Flow

```
Agent identifies MEDIUM/HIGH risk action
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

Safety controls:

- RBAC limits API access by role and permission.
- Low-risk actions such as local workflow generation, log diagnosis, repository scanning, and container listing can run directly.
- Medium-risk actions such as workflow PR creation, fix PR creation, and workflow triggering create a pending approval first.
- High-risk production deployment or destructive actions are not implemented in the MVP.
- GitHub repository modifications happen through a new branch and pull request, never a direct push to `main` or `master`.
- Audit logging records selected agent, intent, risk level, tool/service, status, and summarized result.
- Secrets, tokens, private keys, credentials, and very large logs are redacted or summarized before audit logging where possible.

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
