# Startup Guide

This guide explains how the project is configured and started for local work or demo preparation.

## 1. Prerequisites

Recommended:

- Python 3.11
- Node.js 18 or newer
- npm
- Git

Optional:

- Docker and Docker Compose for full local stack.
- Redis if running background/task features outside Compose.
- PostgreSQL or Supabase-compatible PostgreSQL for production-like testing.

## 2. Environment Files

Backend environment:

```text
backend/.env
```

Frontend environment:

```text
frontend/.env
```

Safe examples are stored in:

```text
backend/.env.example
frontend/.env.example
```

Never commit real tokens, private keys, database passwords, webhook secrets, or JWT secrets.

## 3. Important Backend Values

Minimum local demo values:

```text
DATABASE_URL=sqlite+aiosqlite:///./devops_assistant.db
SECRET_KEY=change-this-for-local-demo
COOKIE_SECURE=false
COOKIE_SAMESITE=lax
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

GitHub local testing:

```text
GITHUB_TOKEN=
GITHUB_REPO_FULL_NAME=
GITHUB_WEBHOOK_SECRET=
```

GitHub App testing:

```text
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY=
GITHUB_APP_WEBHOOK_SECRET=
GITHUB_APP_CLIENT_ID=
GITHUB_APP_CLIENT_SECRET=
```

Model override values are optional when artifacts exist in `backend/app/ml/`:

```text
FAILURE_MODEL_PATH=
FIX_MAPPING_PATH=
```

## 4. Important Frontend Value

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Use the same backend origin that the browser can reach.

## 5. Local Startup Paths

The Makefile contains the preferred developer commands for dependency install, backend, frontend, tests, lint, model training, and full Docker Compose startup.

For architecture and endpoint details, use:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/API_REFERENCE.md](docs/API_REFERENCE.md)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## 6. Default Admin

The backend configuration contains local default admin values:

```text
DEFAULT_ADMIN_EMAIL=admin@example.com
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=admin123
```

For any real deployment, change these values before exposing the app.

## 7. GitHub Permissions

For workflow PR creation, the token or GitHub App needs:

- repository metadata read,
- contents read/write,
- pull requests read/write,
- workflows read/write.

For workflow monitoring/logs, it needs:

- actions read,
- access to the target repository.

For webhook processing, GitHub must be able to reach:

```text
https://your-public-backend/api/v1/webhooks/github
```

`localhost` is not reachable from GitHub.

## 8. Common Problems

### `401 Unauthorized` on `/auth/me`

The browser has no valid access cookie or bearer token. Log in again or clear stale cookies.

### `403 Forbidden`

The user is authenticated but the role lacks the required permission.

### Repository scan fails

Check GitHub token/App installation access and repository name format `owner/repo`.

### Workflow PR fails with insufficient permissions

Enable contents, pull requests, and workflows write permissions on the token or GitHub App.

### Webhook URL rejected by GitHub

Use a public HTTPS URL. GitHub cannot call `localhost`.

### Model unavailable

Check `backend/app/ml/failure_model.joblib` and `backend/app/ml/fix_mapping.joblib`, or configure the override paths.
