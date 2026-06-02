# API Reference

Base API prefix: `/api/v1`

Interactive OpenAPI docs are available from the FastAPI app at `/docs` when the backend is running.

## 1. Authentication Model

The backend accepts access tokens from either:

- `Authorization: Bearer <access_token>`
- the configured httpOnly cookie, default `devops_access_token`

Most browser calls use the cookie. API clients can use bearer tokens.

Public endpoints:

- `GET /health`
- `GET /`
- `GET /api/v1/auth/roles`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/webhooks/github` is public at the HTTP layer but protected by webhook signature verification when configured.

All other protected routes require a valid access token and the required permission.

## 2. Roles And Permissions

| Role | Main permissions |
| --- | --- |
| `viewer` | `agent:chat`, `approvals:read`, `logs:read`, `metrics:read`, `executions:read` |
| `developer` | `agent:chat`, `logs:read`, `metrics:read`, `executions:read`, `deployments:staging` |
| `operator` | developer-level read permissions plus `logs:write`, `executions:write`, `approvals:read`, `approvals:decide`, production/infrastructure permissions |
| `admin` | all permissions |

Only viewer and developer accounts can self-sign up. Operator and admin users must be created by an admin.

## 3. Common Error Shape

```json
{
  "detail": "Human-readable error message."
}
```

Common status codes:

| Code | Meaning |
| --- | --- |
| `400` | Bad request or external service validation failure. |
| `401` | Missing, invalid, or expired token. |
| `403` | Authenticated user lacks required permission. |
| `404` | Requested record was not found. |
| `409` | Approval has already been decided. |
| `410` | Approval expired. |
| `422` | Request validation failed. |
| `500` | Unexpected backend failure. |
| `503` | Required model/provider/service unavailable. |

## 4. Health

### `GET /health`

Checks backend health.

Response:

```json
{
  "status": "ok"
}
```

### `GET /`

Root health/info endpoint.

## 5. Authentication

### `GET /api/v1/auth/roles`

Returns available role profiles and public signup roles.

Response:

```json
{
  "roles": [
    {
      "role": "developer",
      "label": "Developer",
      "description": "Builder workflow...",
      "permissions": ["agent:chat", "executions:read"],
      "can_self_signup": true
    }
  ],
  "public_signup_roles": ["developer", "viewer"]
}
```

### `POST /api/v1/auth/register`

Creates a public viewer/developer account and logs it in.

Request:

```json
{
  "email": "dev@example.com",
  "username": "devuser",
  "password": "password123",
  "role": "developer"
}
```

Response: `LoginResponse`

### `POST /api/v1/auth/login`

Logs in with email/password or legacy username/password. Sets the httpOnly access cookie and returns tokens.

JSON request:

```json
{
  "email": "admin@example.com",
  "password": "admin123"
}
```

Legacy username request is also accepted:

```json
{
  "username": "admin",
  "password": "admin123"
}
```

Response:

```json
{
  "access_token": "jwt-access-token",
  "refresh_token": "jwt-refresh-token",
  "token_type": "bearer",
  "user_id": "uuid",
  "username": "admin",
  "role": "admin",
  "user": {
    "id": "uuid",
    "email": "admin@example.com",
    "username": "admin",
    "role": "admin",
    "is_active": true,
    "created_at": "2026-06-01T00:00:00Z"
  }
}
```

### `POST /api/v1/auth/logout`

Clears the access cookie.

Response: `204 No Content`

### `POST /api/v1/auth/refresh`

Rotates a refresh token and returns a new access/refresh pair.

Request:

```json
{
  "refresh_token": "jwt-refresh-token"
}
```

### `GET /api/v1/auth/me`

Requires authenticated user.

Returns the current user record.

### `GET /api/v1/auth/users`

Required permission: `users:manage` through admin.

Lists users.

### `POST /api/v1/auth/users`

Required permission: `users:manage` through admin.

Creates an admin/operator/developer/viewer account.

Request:

```json
{
  "email": "operator@example.com",
  "username": "operator1",
  "password": "password123",
  "role": "operator",
  "is_active": true
}
```

## 6. Agent APIs

### `POST /api/v1/agent/orchestrate`

Required permission: `agent:chat`

Routes a request through the deterministic multi-agent layer.

Request:

```json
{
  "message": "scan repository owner/repo",
  "context": {
    "repo_full_name": "owner/repo"
  }
}
```

Response:

```json
{
  "selected_agent": "github_agent",
  "intent": "github_scan_repository",
  "risk_level": "low",
  "success": true,
  "result": "Scanned owner/repo: detected python / fastapi...",
  "metadata": {
    "repo_full_name": "owner/repo",
    "file_count": 42
  }
}
```

If approval is required:

```json
{
  "selected_agent": "github_agent",
  "intent": "github_create_workflow_pr",
  "risk_level": "medium",
  "success": false,
  "result": "Human approval is required before executing this action. Approval request ... is pending.",
  "metadata": {
    "approval_required": true,
    "approval_id": "uuid"
  }
}
```

### `POST /api/v1/agent/chat`

Required permission: `agent:chat`

Legacy LangChain chat route.

Request:

```json
{
  "message": "Generate a summary of recent workflow runs",
  "session_id": "optional-session-id"
}
```

Response:

```json
{
  "output": "Agent response text",
  "session_id": "session-id",
  "intermediate_steps": [
    {
      "tool": "github_recent_runs",
      "input": {},
      "output": "tool output"
    }
  ],
  "requires_approval": false,
  "approval_id": null
}
```

### `DELETE /api/v1/agent/session/{session_id}`

Required permission: `agent:chat`

Clears in-process and persisted chat history for a session.

### WebSocket `/api/v1/agent/ws/agent`

Streams legacy chat output. The app also keeps legacy WebSocket aliases:

- `/api/agent/ws/agent`
- `/ws/ws/agent`
- `/ws/agent`

Auth token can come from cookie, bearer header, or `token` query parameter.

## 7. CI/CD APIs

### `POST /api/v1/cicd/analyze-files`

Analyzes a list of repository file paths without calling GitHub.

Request:

```json
{
  "files": ["package.json", "src/App.tsx", "package-lock.json"]
}
```

Response:

```json
{
  "language": "javascript",
  "framework": "react",
  "package_manager": "npm",
  "has_docker": false,
  "has_existing_workflows": false,
  "recommended_workflow": "node",
  "project_dir": ".",
  "detected_projects": [],
  "ci_warnings": []
}
```

### `POST /api/v1/cicd/generate-workflow`

Analyzes file paths and returns GitHub Actions YAML.

Request:

```json
{
  "files": ["requirements.txt", "app/main.py", "tests/test_app.py"]
}
```

Response:

```json
{
  "stack": {
    "language": "python",
    "framework": "fastapi",
    "package_manager": "pip",
    "has_docker": false,
    "has_existing_workflows": false,
    "recommended_workflow": "python",
    "project_dir": ".",
    "detected_projects": [],
    "ci_warnings": []
  },
  "path": ".github/workflows/ai-generated-ci.yml",
  "workflow_yaml": "name: AI Generated CI\n..."
}
```

## 8. Repository APIs

### `GET /api/v1/repositories/installed`

Required permission: `logs:read`

Lists repositories installed through the GitHub App.

### `POST /api/v1/repositories/scan`

Required permission: `logs:read`

Fetches repository tree and selected manifest/workflow contents, detects stack, and returns readiness.

Request:

```json
{
  "repo_full_name": "owner/repo",
  "branch": "main"
}
```

Response:

```json
{
  "repo_full_name": "owner/repo",
  "files": ["package.json", ".github/workflows/ci.yml"],
  "stack": {
    "language": "javascript",
    "framework": "react",
    "package_manager": "npm",
    "has_docker": false,
    "has_existing_workflows": true,
    "recommended_workflow": "node",
    "project_dir": ".",
    "detected_projects": [],
    "ci_warnings": []
  },
  "readiness": {
    "score": 82,
    "grade": "B",
    "summary": "Repository is mostly ready for CI/CD.",
    "strengths": ["Lockfile found"],
    "findings": [],
    "recommended_next_actions": ["Review generated workflow before merging"]
  }
}
```

### `POST /api/v1/repositories/create-workflow-pr`

Required permission: `executions:write`

Creates an approval request when HITL is enabled. After approval, the backend creates a branch, commits generated workflow YAML, and opens a pull request.

Request:

```json
{
  "repo_full_name": "owner/repo",
  "overwrite_existing_workflow": false
}
```

Approval response:

```json
{
  "repo_full_name": "owner/repo",
  "status": "approval_required",
  "approval_required": true,
  "approval_id": "uuid",
  "message": "Human approval is required before creating the workflow pull request."
}
```

Direct execution response when HITL is disabled:

```json
{
  "repo_full_name": "owner/repo",
  "detected_stack": {
    "language": "python",
    "framework": "fastapi",
    "package_manager": "pip",
    "has_docker": true,
    "has_existing_workflows": false,
    "recommended_workflow": "python",
    "project_dir": ".",
    "detected_projects": [],
    "ci_warnings": []
  },
  "branch": "ai-cicd/setup-pipeline-20260601102429",
  "workflow_path": ".github/workflows/ai-generated-ci.yml",
  "pull_request_url": "https://github.com/owner/repo/pull/1"
}
```

## 9. Failure Prediction API

### `POST /api/v1/model/predict-failure`

Required permission: `logs:read`

Classifies CI/CD logs with the trained model.

Request:

```json
{
  "log_text": "Run npm test\nnpm ERR! Missing script: \"test\""
}
```

Response:

```json
{
  "label": "npm_missing_test_script",
  "confidence": 0.82,
  "suggested_fix": "Add a test script to package.json or update CI to run the correct npm script.",
  "recommendation": {
    "summary": "Missing npm test script",
    "risk_level": "low",
    "requires_approval": false
  }
}
```

## 10. GitHub Webhooks

### `POST /api/v1/webhooks/github`

Receives GitHub App and workflow events.

Important headers:

- `X-Hub-Signature-256: sha256=<hmac>`
- `X-GitHub-Event: workflow_run`

Supported events:

- `installation`
- `installation_repositories`
- `workflow_run` with `action=completed` and `conclusion=failure`

Response:

```json
{
  "received": true,
  "event": "workflow_run"
}
```

For failed workflow runs, the backend downloads logs, predicts failure category, stores a `WorkflowFailure`, and writes an `Execution`.

## 11. Workflow Failure APIs

### `GET /api/v1/workflow-failures`

Required permission: `executions:read`

Query parameters:

- `limit`
- `repo_full_name`
- `status`

Lists stored GitHub Actions failure diagnoses.

### `GET /api/v1/workflow-failures/{failure_id}`

Required permission: `executions:read`

Returns one workflow failure diagnosis.

### `POST /api/v1/workflow-failures/{failure_id}/create-fix-pr`

Required permission: `executions:write`

Creates a selected safe fix PR or returns an approval requirement depending on the failure and risk.

Response:

```json
{
  "workflow_failure_id": "uuid",
  "repo_full_name": "owner/repo",
  "status": "approval_required",
  "approval_id": "uuid",
  "branch": null,
  "workflow_path": null,
  "pull_request_url": null,
  "message": "Human approval is required before creating this fix PR.",
  "recommendation": {},
  "approval_details": {}
}
```

## 12. Approval APIs

### `GET /api/v1/approvals`

Required permission: `approvals:read`

Query parameters:

- `status_filter`, default `pending`

Lists approval requests.

### `GET /api/v1/approvals/{approval_id}`

Required permission: `approvals:read`

Returns one approval request.

### `POST /api/v1/approvals/{approval_id}/decide`

Required permission: `approvals:decide`

Approves or rejects a pending request.

Request:

```json
{
  "approved": true,
  "note": "Reviewed and approved."
}
```

Response includes approval status, decider, execution ID, and execution details.

## 13. Execution And Audit APIs

### `GET /api/v1/executions`

Required permission: `executions:read`

Query parameters:

- `limit`, default `50`, max `200`
- `tool`
- `status`
- `actor`
- `source`
- `days`, default `7`

Also available through `/api/v1/audit`.

### `GET /api/v1/executions/{execution_id}`

Required permission: `executions:read`

Returns one execution record.

## 14. Legacy Aliases

The app keeps legacy aliases for compatibility:

- `/api/agent/*` mirrors `/api/v1/agent/*`
- `/api/v1/audit/*` mirrors `/api/v1/executions/*`
- `/ws/agent` maps directly to the agent WebSocket
