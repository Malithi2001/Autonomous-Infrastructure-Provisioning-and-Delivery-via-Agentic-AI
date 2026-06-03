# Startup Guide

This guide explains how to configure and start the project for local development, supervisor demos, desktop mode, mobile packaging, and Docker Compose.

## 1. Prerequisites

Required:

- Python 3.11. Python 3.13 is not supported for this MVP because pinned ML packages can fail to install.

Recommended:

- Node.js 18 or newer
- npm
- Git

Optional:

- Docker and Docker Compose for the full local stack.
- Redis if running background/task features outside Compose.
- PostgreSQL or Supabase-compatible PostgreSQL for production-like testing.
- Android Studio for Capacitor Android builds.
- PowerShell on Windows for desktop installer scripts.

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
.env.example
```

Create local files with the Makefile helper. It copies from the examples only when the target `.env` file is missing, so existing local secrets are never overwritten:

```bash
make init-env
```

Never commit real tokens, private keys, database passwords, webhook secrets, JWT secrets, or local database files.

## 3. Minimum Local Web Demo

Install dependencies:

```bash
make setup
```

`make setup` also runs `make init-env`, so a fresh clone gets the required local environment files before dependency installation.

Start the backend:

```bash
make backend
```

Start the frontend in another terminal:

```bash
make frontend
```

Open:

```text
Frontend: http://localhost:5173
Backend health: http://localhost:8000/health
OpenAPI docs: http://localhost:8000/docs
```

Default demo admin values:

```text
DEFAULT_ADMIN_EMAIL=admin@example.com
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=admin123
```

These are for local demo databases only. Change them before any shared or public deployment.

## 4. Important Backend Values

Minimum local values:

```text
DATABASE_URL=sqlite+aiosqlite:///./devops_assistant.db
SECRET_KEY=change-this-for-local-demo
COOKIE_SECURE=false
COOKIE_SAMESITE=lax
ALLOWED_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
```

GitHub PAT fallback for local MVP testing:

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

Required model artifacts:

```text
backend/app/ml/failure_model.joblib
backend/app/ml/fix_mapping.joblib
```

Retrain the model:

```bash
make train-model
```

## 5. Important Frontend Values

For local browser development:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_DESKTOP_MODE=false
VITE_MOBILE_MODE=false
VITE_DISABLE_AUTH=false
```

Use the same backend origin that the browser, desktop shell, phone, or emulator can reach.

## 6. Docker Compose Startup

Docker Compose starts PostgreSQL, Redis, backend, frontend, Celery worker, and Flower.

```bash
make init-env
make dev
```

Build and start:

```bash
make init-env
make dev-build
```

Ports:

```text
Frontend: http://localhost:5173
Backend: http://localhost:8000
Flower: http://localhost:5555
PostgreSQL: localhost:5432
Redis: localhost:6379
```

Stop services:

```bash
make docker-down
```

View logs:

```bash
make docker-logs
```

The Compose backend reads `backend/.env`, then overrides database and Redis URLs for the container network. Run `make init-env` first on a clean submission checkout because real `.env` files are intentionally excluded from the submission ZIP.

## 7. Desktop Mode

Desktop mode is for local single-user demos. It bypasses JWT/RBAC, opens as `Desktop User`, hides Users & Roles and Sign out, and keeps audit logs and approval gates.

Environment:

```text
DESKTOP_MODE=true
DISABLE_AUTH=true
VITE_DESKTOP_MODE=true
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Run desktop development mode:

```bash
make desktop-dev
```

Build the Windows installer from PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\desktop\setup-windows.ps1
```

Run from source after setup:

```powershell
.\desktop\run-desktop.ps1
```

Check desktop build prerequisites:

```bash
make desktop-check
```

## 8. Mobile Mode

The mobile app packages the React frontend with Capacitor. It does not run the backend on the phone.

For local phone testing, start the backend on a LAN-reachable host:

```bash
cd backend
DESKTOP_MODE=true DISABLE_AUTH=true HOST=0.0.0.0 PORT=8000 ./venv/bin/python run_backend.py
```

Configure `VITE_API_BASE_URL` so the app can reach that backend.

Build and sync Android:

```bash
make mobile-sync
make mobile-open-android
```

Build a debug APK:

```bash
make mobile-apk-debug
```

See [docs/MOBILE_APP.md](docs/MOBILE_APP.md) for emulator, LAN IP, ngrok, Android Studio, and APK troubleshooting.

## 9. GitHub Permissions

For workflow PR creation, the token or GitHub App needs:

- repository metadata read,
- contents read/write,
- pull requests read/write,
- workflows read/write.

For workflow monitoring and log downloads, it needs:

- actions read,
- access to the target repository.

For webhook processing, GitHub must be able to reach:

```text
https://your-public-backend/api/v1/webhooks/github
```

`localhost` is not reachable from GitHub. Use a public HTTPS tunnel for local webhook testing.

## 10. Common Problems

### Backend venv missing

Run:

```bash
make backend-install
```

### Frontend dependencies missing

Run:

```bash
make frontend-install
```

### `401 Unauthorized` on `/auth/me`

The browser has no valid access cookie or bearer token. Log in again or clear stale cookies.

### `403 Forbidden`

The user is authenticated but the role lacks the required permission.

### Repository scan fails

Check GitHub token or GitHub App installation access and repository name format `owner/repo`.

### Workflow PR fails with insufficient permissions

Enable contents, pull requests, and workflows write permissions on the token or GitHub App.

### Webhook URL rejected by GitHub

Use a public HTTPS URL. GitHub cannot call `localhost`.

### Model unavailable

Check `backend/app/ml/failure_model.joblib` and `backend/app/ml/fix_mapping.joblib`, or configure override paths.

### CORS or cookie issues

Check:

```text
ALLOWED_ORIGINS
COOKIE_SECURE
COOKIE_SAMESITE
VITE_API_BASE_URL
```

For local HTTP demos, `COOKIE_SECURE=false` is expected. For HTTPS deployments, use `COOKIE_SECURE=true`.
