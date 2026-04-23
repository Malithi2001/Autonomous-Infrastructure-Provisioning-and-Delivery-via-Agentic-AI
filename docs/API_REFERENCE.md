# API Reference

Base URL: `http://localhost:8000/api/v1`
Interactive docs: `http://localhost:8000/docs`

---

## Authentication

All endpoints (except `/health` and `/auth/login`) require a Bearer JWT token.

```
Authorization: Bearer <access_token>
```

---

## Endpoints

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |

**Response:**
```json
{ "status": "ok", "service": "Smart DevOps Assistant" }
```

---

### Authentication

#### `POST /auth/login`
Login and receive a JWT token.

**Request** (form-data):
```
username=admin
password=yourpassword
```

**Response:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user_id": "uuid",
  "username": "admin",
  "role": "admin"
}
```

#### `POST /auth/register`
Register a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "username": "devops_engineer",
  "password": "securepassword123"
}
```

---

### Agent

#### `POST /agent/chat`
Send a natural language DevOps command to the AI agent.

**Required permission:** `agent:chat`

**Request:**
```json
{
  "message": "List all running Docker containers",
  "session_id": "optional-uuid-for-continuity"
}
```

**Response:**
```json
{
  "output": "Here are the running containers:\n- [running] nginx (ports: 80->80/tcp)...",
  "session_id": "generated-or-provided-uuid",
  "intermediate_steps": [
    {
      "tool": "docker_list_containers",
      "tool_input": {},
      "output": "- [running] nginx..."
    }
  ],
  "requires_approval": false,
  "approval_id": null
}
```

**When `requires_approval: true`:**
```json
{
  "output": "This action requires human approval before I can proceed.",
  "requires_approval": true,
  "approval_id": "approval-uuid"
}
```

#### `DELETE /agent/session/{session_id}`
Clear a conversation session and its memory.

---

### HITL Approvals

#### `GET /approvals`
List all pending approval requests.

**Required permission:** `logs:read`

**Response:**
```json
[
  {
    "id": "uuid",
    "execution_id": "uuid",
    "description": "Deploy docker image 'myapp:latest' to production EC2",
    "status": "pending",
    "expires_at": "2025-01-01T12:05:00Z",
    "created_at": "2025-01-01T12:00:00Z"
  }
]
```

#### `POST /approvals/{approval_id}/decide`
Approve or reject a pending action.

**Required permission:** `deployments:production`

**Request:**
```json
{
  "approved": true,
  "note": "Reviewed deployment manifest, looks good."
}
```

---

### Executions

#### `GET /executions?limit=50`
List recent agent executions (audit log).

**Required permission:** `executions:read`

**Response:**
```json
[
  {
    "id": "uuid",
    "session_id": "session-uuid",
    "command": "Restart the nginx container",
    "status": "success",
    "risk_level": "medium",
    "tool_used": "docker_restart_container",
    "result": "Container 'nginx' restarted successfully.",
    "created_at": "2025-01-01T12:00:00Z",
    "completed_at": "2025-01-01T12:00:03Z"
  }
]
```

#### `GET /executions/{execution_id}`
Get full detail of a specific execution.

---

### Webhooks

#### `POST /webhooks/github`
Receive GitHub Actions events (workflow_run, push, etc.)

**Headers required:**
```
X-Hub-Signature-256: sha256=<hmac>
X-GitHub-Event: workflow_run
```

Configures GitHub repo → Settings → Webhooks → `http://your-server/api/v1/webhooks/github`

---

## Risk Levels

| Level | Description | Requires Approval |
|-------|-------------|-------------------|
| `low` | Read-only operations (list, logs, metrics) | No |
| `medium` | Container restarts, non-prod deployments | No |
| `high` | Production deployments, infra changes | **Yes** |
| `critical` | Destructive operations, data deletion | **Yes** |

---

## Error Responses

```json
{
  "detail": "Human-readable error message"
}
```

| Code | Meaning |
|------|---------|
| 400 | Bad request / validation error |
| 401 | Missing or invalid JWT token |
| 403 | Insufficient permissions for this action |
| 404 | Resource not found |
| 500 | Server / agent error |
