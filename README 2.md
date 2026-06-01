# Agentic AI-Powered Smart DevOps Assistant

An MVP DevOps assistant for diagnosing failed CI/CD logs, generating GitHub Actions workflows, and demonstrating how agentic AI can support safer software delivery.

This project is a Final Year Research Project for the BSc (Hons.) in Information Technology at Horizon Campus, Faculty of Information Technology.

Supervisor: Isuru Samarappulige<br>
Co-supervisor: Anuradha Ishani Yapa

## Problem Statement

Modern CI/CD and infrastructure workflows fail for many repeated reasons: missing lockfiles, broken test scripts, dependency conflicts, Docker build errors, and language-specific setup mistakes. Developers often lose time searching logs, mapping failure messages to causes, and writing or repairing workflow files manually.

This project explores how an AI-assisted DevOps platform can reduce that troubleshooting time by combining:

- a trained failure classification model for CI/CD logs,
- deterministic repository stack detection,
- GitHub Actions workflow generation,
- a FastAPI backend with RBAC and audit-oriented endpoints,
- a React frontend for demo-friendly interaction,
- a path toward GitHub App automation that can open pull requests with generated fixes.

## MVP Features

- Authentication and role-based access control for demo users.
- React/Vite dashboard with Agent Chat, Approvals, Executions, Users, and CI/CD Assistant pages.
- Failure Log Classifier page for pasting a failed CI/CD log and receiving:
  - predicted failure label,
  - confidence score,
  - suggested fix.
- Workflow Generator page for entering repository file paths and receiving:
  - detected language/framework/package manager,
  - recommended workflow type,
  - generated GitHub Actions YAML.
- REST endpoints for prediction and workflow generation.
- GitHub webhook handling for failed workflow-run events.
- GitHub tool support for creating a branch, committing generated workflow YAML, and opening a PR.

## Trained Model Explanation

The MVP model lives in `backend/app/ml/`.

- Dataset: `backend/app/ml/dataset.csv`
- Training script: `backend/app/ml/train_failure_model.py`
- Model artifact: `backend/app/ml/failure_model.joblib`
- Suggested-fix mapping: `backend/app/ml/fix_mapping.joblib`

The training script loads labeled CI/CD log examples with three required columns:

- `log_text`
- `label`
- `suggested_fix`

It trains a scikit-learn pipeline:

- `TfidfVectorizer` converts raw log text into text features.
- `LogisticRegression` classifies the likely failure category.
- A label-to-fix mapping is saved separately so the prediction API can return a practical remediation hint.

The prediction endpoint returns:

```json
{
  "label": "npm_missing_test_script",
  "confidence": 0.82,
  "suggested_fix": "Add a test script to package.json or update CI to run the correct npm script."
}
```

## Setup Instructions

### Prerequisites

- Python 3.11
- Node.js 18+
- npm
- Docker and Docker Compose, optional
- PostgreSQL or Supabase Postgres for the full app database

### Install Dependencies

From the project root:

```bash
make setup
```

Or install manually:

```bash
python3.11 -m venv backend/venv
backend/venv/bin/python -m pip install --upgrade pip
backend/venv/bin/python -m pip install -r backend/requirements.txt
cd frontend
npm install
```

### Environment

Create or update:

- `backend/.env`
- `frontend/.env`

You can start from the checked-in examples:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Important local values:

```bash
# backend/.env
DATABASE_URL=postgresql://...
SECRET_KEY=change-me-for-local-demo
COOKIE_SECURE=False
COOKIE_SAMESITE=lax
ALLOWED_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
GITHUB_TOKEN=
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY=
GITHUB_APP_WEBHOOK_SECRET=
```

```bash
# frontend/.env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

If `frontend/.env` points to another port, start the backend on that same port or update `VITE_API_BASE_URL`.

## How to Train the Model

From the project root:

```bash
cd backend
venv/bin/python app/ml/train_failure_model.py
```

Expected result:

- printed accuracy and classification report,
- refreshed `backend/app/ml/failure_model.joblib`,
- refreshed `backend/app/ml/fix_mapping.joblib`.
- refreshed report files under `backend/app/ml/reports/`.

The backend loads these artifacts lazily when `/api/v1/model/predict-failure` is called. Docker Compose mounts `backend/app/ml` into the backend container, so retraining locally updates the model used by the container without rebuilding the image.

## How to Run Backend and Frontend

### Option 1: Makefile

Terminal 1:

```bash
make dev-backend
```

Terminal 2:

```bash
make dev-frontend
```

Default URLs:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

### Option 2: Manual Commands

Terminal 1:

```bash
cd backend
venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Terminal 2:

```bash
cd frontend
npm run dev
```

### Option 3: Docker Compose

Prepare env files first:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

For Docker Compose, keep `backend/.env` development-safe and let Compose override the database host to the `db` service. Do not put real GitHub tokens or private keys in committed files.

```bash
docker compose up -d --build
```

Useful Docker commands:

```bash
docker compose ps
docker compose logs -f backend
docker compose down
```

Docker URLs:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

The frontend image is built with `VITE_API_BASE_URL`. The Compose default is `http://localhost:8000`, which works for local browser demos because the backend port is published on the host.

## Demo Login Accounts

Seeded demo users include:

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@example.com` | `admin123` |
| Operator | `operator@devops.example.com` | `operator123` |
| Developer | `devops.engineer@example.com` | `developer123` |
| Viewer | `viewer@company.example.com` | `viewer123` |

For the MVP demo, `viewer@company.example.com` is enough to test prediction and workflow generation.

## How to Test the Prediction Endpoint

Start the backend, then log in and save the auth cookie:

```bash
curl -i -sS -c /tmp/devops_demo_cookie.txt \
  -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"viewer@company.example.com","password":"viewer123"}'
```

Call the prediction endpoint:

```bash
curl -i -sS -b /tmp/devops_demo_cookie.txt \
  -X POST http://127.0.0.1:8000/api/v1/model/predict-failure \
  -H "Content-Type: application/json" \
  -d '{"log_text":"npm test failed: npm ERR! Missing script: test. To see a list of scripts, run npm run."}'
```

Expected shape:

```json
{
  "label": "npm_missing_test_script",
  "confidence": 0.0,
  "suggested_fix": "Add a test script to package.json or update CI to run the correct npm script."
}
```

The exact confidence may vary after retraining.

## How to Test the Workflow Generation Endpoint

Start the backend, then call:

```bash
curl -i -sS \
  -X POST http://127.0.0.1:8000/api/v1/cicd/generate-workflow \
  -H "Content-Type: application/json" \
  -d '{"files":["package.json","package-lock.json","src/App.tsx","vite.config.ts","Dockerfile"]}'
```

Expected shape:

```json
{
  "stack": {
    "language": "javascript",
    "framework": "react",
    "package_manager": "npm",
    "has_docker": true,
    "has_existing_workflows": false,
    "recommended_workflow": "node-ci"
  },
  "path": ".github/workflows/ai-generated-ci.yml",
  "workflow_yaml": "name: AI Generated CI\n..."
}
```

## Frontend MVP Demo Page

Open the frontend and navigate to:

```text
http://localhost:5173/diagnosis
```

Use the CI/CD Assistant page to:

1. Paste a failed CI/CD log.
2. Click `Predict Failure`.
3. Review label, confidence, and suggested fix.
4. Enter a repository file list, one file per line.
5. Click `Generate Workflow`.
6. Review the detected stack and generated YAML.

## Tests and Quality Checks

Backend tests:

```bash
make test-backend
```

Frontend build:

```bash
cd frontend
npm run build
```

Frontend lint, if dependencies are installed:

```bash
make lint-frontend
```

## Project Structure

```text
backend/
  app/api/routes/          FastAPI route modules
  app/ml/                  dataset, training script, trained model artifacts
  app/services/            failure prediction, repo analysis, workflow generation
  app/tools/               GitHub, Docker, shell, monitoring tools
  tests/                   pytest suite

frontend/
  src/pages/               dashboard pages, including CI/CD Assistant
  src/services/api.ts      frontend API client
  src/components/          shared UI and layout components

database/
  supabase_rbac_schema_seed.sql

docs/
  MVP_DEMO.md
```

## Future Work

- Convert the GitHub PR helper into a complete GitHub App flow.
- Pull real failed workflow logs from GitHub Actions automatically.
- Generate repository-specific workflow updates and open pull requests for supervisor-approved changes.
- Expand the model dataset with more failure classes and real CI/CD logs.
- Add evaluation metrics and model versioning for repeatable research results.
