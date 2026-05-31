# Agentic AI-Powered Smart DevOps Assistant

A web-based CI/CD automation and failure-diagnosis system for autonomous software delivery support, built as a final-year research project.

This project is a Final Year Research Project for the BSc (Hons.) in Information Technology at Horizon Campus, Faculty of Information Technology.

Supervisor: Isuru Samarappulige  
Co-supervisor: Anuradha Ishani Yapa

## Problem Statement

Modern software teams depend heavily on CI/CD pipelines, but many pipeline failures are repetitive and time-consuming to diagnose. Developers often inspect long workflow logs manually, identify missing dependencies or configuration issues, and then write or update GitHub Actions workflows by hand. This slows delivery and increases the chance of unsafe automation when fixes are applied without review.

This project addresses that gap by combining trained CI/CD failure classification, deterministic repository analysis, GitHub Actions workflow generation, pull request automation, human approval, and audit logging in one demo-friendly DevOps assistant.

## Research Aim

The aim is to design and evaluate an agentic AI-powered Smart DevOps Assistant that can reduce manual effort in CI/CD setup and failure diagnosis while preserving safety through human-in-the-loop approval and auditable actions.

The project focuses on these research questions:

- Can a trained text classification model identify common CI/CD failure categories from workflow logs?
- Can repository structure be analyzed automatically to recommend and generate suitable GitHub Actions workflows?
- Can safe CI/CD fixes be proposed or opened as pull requests without directly modifying protected branches?
- Can human approval and audit logging make automation more trustworthy for DevOps workflows?

## System Features

- FastAPI backend with authentication, RBAC, and REST APIs.
- React frontend for a simple final-demo workflow.
- Trained ML model for CI/CD failure classification.
- Failure prediction response with label, confidence, suggested fix, and recommendation details.
- Repository file analysis for Node.js, React, Python, FastAPI, Java/Maven, Docker, and existing workflows.
- GitHub Actions workflow generation for supported stacks.
- GitHub repository scanning through API.
- Workflow setup pull request creation on a new branch.
- GitHub webhook handling for failed workflow-run events.
- Real GitHub Actions log download, cleanup, and redaction.
- Persistent workflow failure diagnosis records.
- Safe fix recommendation engine.
- Low-risk fix pull request generation for selected failure types.
- Human-in-the-loop approval for higher-risk fix PR actions.
- Audit log records for model, GitHub, approval, and automation actions.

## Architecture Overview

```text
React Frontend
  - CI/CD Assistant
  - Repository CI/CD Setup
  - Workflow Failures
  - Approvals
  - Audit
        |
        v
FastAPI Backend
  - Auth and RBAC
  - Model prediction API
  - CI/CD analysis and workflow generation APIs
  - Repository scan and PR APIs
  - GitHub webhook API
  - Approval and audit APIs
        |
        +--> ML service
        |      - TF-IDF + Logistic Regression model
        |      - fix mapping
        |      - recommendation service
        |
        +--> GitHub service/tooling
        |      - repository tree scan
        |      - workflow log download
        |      - branch/file/PR operations
        |      - GitHub App installation support
        |
        +--> Database
               - users and sessions
               - approval requests
               - executions/audit records
               - workflow failures
               - repository installations
```

Main technologies:

- Backend: FastAPI, SQLAlchemy, Pydantic, pytest
- Frontend: React, Vite, TypeScript, Tailwind CSS
- ML: scikit-learn, pandas, joblib
- Automation: GitHub REST API, GitHub Actions
- Storage: SQLite for local demo, PostgreSQL/Supabase compatible schema for deployment
- Optional services: Redis, Celery, Docker Compose

## Trained Model Explanation

The CI/CD failure model is stored under `backend/app/ml/`.

- Dataset: `backend/app/ml/dataset.csv`
- Training script: `backend/app/ml/train_failure_model.py`
- Model artifact: `backend/app/ml/failure_model.joblib`
- Suggested-fix mapping: `backend/app/ml/fix_mapping.joblib`
- Reports: `backend/app/ml/reports/`

The training pipeline:

1. Loads the dataset.
2. Cleans null values.
3. Removes duplicate rows.
4. Uses a stratified train/test split where class sizes allow it.
5. Trains a TF-IDF plus Logistic Regression pipeline.
6. Optionally compares a LinearSVC model.
7. Prints accuracy, precision, recall, and F1-score.
8. Saves model, fix mapping, metrics JSON, classification report, and confusion matrix image.

Prediction output includes:

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

## Dataset Description

The dataset uses three required columns:

- `log_text`: realistic CI/CD failure log text
- `label`: failure category
- `suggested_fix`: human-readable remediation guidance

Supported labels include:

- `npm_missing_lockfile`
- `npm_missing_test_script`
- `npm_install_failed`
- `npm_build_failed`
- `python_missing_dependency`
- `pytest_not_found`
- `module_not_found`
- `maven_test_failed`
- `docker_build_failed`
- `wrong_runtime_version`
- `unknown_failure`

The current dataset contains GitHub Actions-style examples for Node.js, React, Python, FastAPI, Java/Maven, Docker, runtime mismatch, dependency, build, and unknown failure cases. It does not include real secrets, private repository URLs, real tokens, or private usernames.

## Setup Instructions

### Prerequisites

- Python 3.11
- Node.js 18 or newer
- npm
- Docker and Docker Compose, optional
- GitHub personal access token or GitHub App credentials, optional for GitHub demos

### Environment Files

From the project root:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Important backend variables:

```bash
DATABASE_URL=sqlite+aiosqlite:///./devops_assistant.db
SECRET_KEY=change-this-for-local-demo
COOKIE_SECURE=false
COOKIE_SAMESITE=lax
ALLOWED_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
GITHUB_TOKEN=
GITHUB_WEBHOOK_SECRET=
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY=
GITHUB_APP_WEBHOOK_SECRET=
GITHUB_APP_CLIENT_ID=
GITHUB_APP_CLIENT_SECRET=
FAILURE_MODEL_PATH=
FIX_MAPPING_PATH=
```

Important frontend variable:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Never commit real tokens, private keys, webhook secrets, or production database passwords.

### Install Dependencies

Using the Makefile:

```bash
make setup
```

Manual backend setup:

```bash
python3.11 -m venv backend/venv
backend/venv/bin/python -m pip install --upgrade pip
backend/venv/bin/python -m pip install -r backend/requirements.txt
```

Manual frontend setup:

```bash
cd frontend
npm install
```

## Developer Commands

The root `Makefile` provides the main local development workflow:

```bash
make setup
```

Installs backend and frontend dependencies when the required manifests are present.

```bash
make dev
```

Starts the full project with Docker Compose.

```bash
make train-model
```

Runs the CI/CD failure classification training script and refreshes model artifacts.

```bash
make test
```

Runs backend tests and frontend tests if a frontend test script is configured.

```bash
make clean
```

Removes safe generated cache/build files only, such as Python bytecode, pytest cache, coverage files, frontend build output, and temporary logs. It does not delete source code, tests, docs, datasets, trained model files, `.env.example`, Docker files, dependency lock files, or database volumes.

## Model Training Instructions

Train locally outside Docker:

```bash
cd backend
venv/bin/python app/ml/train_failure_model.py
```

Expected outputs:

- `backend/app/ml/failure_model.joblib`
- `backend/app/ml/fix_mapping.joblib`
- `backend/app/ml/reports/metrics.json`
- `backend/app/ml/reports/classification_report.txt`
- `backend/app/ml/reports/confusion_matrix.png`

Docker Compose mounts `backend/app/ml` into the backend container, so retraining locally updates the model artifacts used by Docker without rebuilding the backend image.

## Backend Run Instructions

Run locally:

```bash
cd backend
venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend URLs:

- API root: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

Run backend tests:

```bash
cd backend
venv/bin/python -m pytest tests -q
```

Run backend tests with coverage:

```bash
cd backend
venv/bin/python -m pytest tests -q --cov=app --cov-report=term-missing
```

## Frontend Run Instructions

Run locally:

```bash
cd frontend
npm run dev
```

Open:

```text
http://localhost:5173
```

Build frontend:

```bash
cd frontend
npm run build
```

## Docker Run Instructions

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up -d --build
```

Useful commands:

```bash
docker compose ps
docker compose logs -f backend
docker compose down
```

Docker URLs:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## GitHub Integration Setup

### Local PAT Flow

For local testing, set:

```bash
GITHUB_TOKEN=your_github_token_here
GITHUB_WEBHOOK_SECRET=local_webhook_secret
```

Recommended token permissions for repository automation:

- `contents: read/write`
- `pull_requests: read/write`
- `actions: read`
- access to the target repository

The system must not push directly to `main` or `master`. Workflow and fix changes are made on new branches and opened as pull requests.

### GitHub App Flow

For real repository installation demos, configure:

```bash
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY=
GITHUB_APP_WEBHOOK_SECRET=
GITHUB_APP_CLIENT_ID=
GITHUB_APP_CLIENT_SECRET=
```

GitHub App permissions:

- Contents: read and write
- Pull requests: read and write
- Actions: read
- Metadata: read

Webhook events:

- `workflow_run`
- `installation`
- `installation_repositories`

Webhook URL:

```text
https://your-public-backend-url/api/v1/webhooks/github
```

For local webhook testing, use a tunnel such as ngrok and point the GitHub App or repository webhook to the tunnel URL.

## API Examples

Login and save cookie:

```bash
curl -i -sS -c /tmp/devops_demo_cookie.txt \
  -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"operator@devops.example.com","password":"operator123"}'
```

Predict failure:

```bash
curl -i -sS -b /tmp/devops_demo_cookie.txt \
  -X POST http://127.0.0.1:8000/api/v1/model/predict-failure \
  -H "Content-Type: application/json" \
  -d '{"log_text":"npm ERR! Missing script: test"}'
```

Analyze repository file list:

```bash
curl -i -sS -b /tmp/devops_demo_cookie.txt \
  -X POST http://127.0.0.1:8000/api/v1/cicd/analyze-files \
  -H "Content-Type: application/json" \
  -d '{"files":["package.json","src/App.jsx","vite.config.js","Dockerfile"]}'
```

Generate workflow YAML:

```bash
curl -i -sS -b /tmp/devops_demo_cookie.txt \
  -X POST http://127.0.0.1:8000/api/v1/cicd/generate-workflow \
  -H "Content-Type: application/json" \
  -d '{"files":["package.json","package-lock.json","src/App.tsx","vite.config.ts","Dockerfile"]}'
```

Scan GitHub repository:

```bash
curl -i -sS -b /tmp/devops_demo_cookie.txt \
  -X POST http://127.0.0.1:8000/api/v1/repositories/scan \
  -H "Content-Type: application/json" \
  -d '{"repo_full_name":"owner/repo","branch":"main"}'
```

Create workflow setup PR:

```bash
curl -i -sS -b /tmp/devops_demo_cookie.txt \
  -X POST http://127.0.0.1:8000/api/v1/repositories/create-workflow-pr \
  -H "Content-Type: application/json" \
  -d '{"repo_full_name":"owner/repo"}'
```

List workflow failures:

```bash
curl -i -sS -b /tmp/devops_demo_cookie.txt \
  http://127.0.0.1:8000/api/v1/workflow-failures
```

Create fix PR for a workflow failure:

```bash
curl -i -sS -b /tmp/devops_demo_cookie.txt \
  -X POST http://127.0.0.1:8000/api/v1/workflow-failures/{failure_id}/create-fix-pr
```

List audit records:

```bash
curl -i -sS -b /tmp/devops_demo_cookie.txt \
  "http://127.0.0.1:8000/api/v1/audit?limit=50&tool=github&status=success"
```

## Demo Flow

Recommended final demo:

1. Train the model and show generated metrics.
2. Start backend and frontend.
3. Log in as an operator.
4. Open CI/CD Assistant and paste a failed CI/CD log.
5. Show predicted label, confidence, suggested fix, and recommendation.
6. Open Repository CI/CD Setup.
7. Enter a GitHub repository full name.
8. Scan repository and show detected stack.
9. Create a workflow setup PR and open the PR URL.
10. Trigger or simulate a failed GitHub Actions run.
11. Open Workflow Failures and show stored diagnosis.
12. Create a fix PR if available.
13. If approval is required, approve it from the Approvals page.
14. Open Audit and show the recorded actions.

Detailed script: `docs/FINAL_DEMO.md`.

## Demo Login Accounts

Seeded demo users include:

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@example.com` | `admin123` |
| Operator | `operator@devops.example.com` | `operator123` |
| Developer | `devops.engineer@example.com` | `developer123` |
| Viewer | `viewer@company.example.com` | `viewer123` |

## Limitations

- The trained model uses a curated synthetic/demo dataset and should be expanded with more real-world CI/CD logs before production use.
- Confidence scores depend on the current dataset and should be interpreted as assistant guidance, not a final decision.
- Safe fix PR generation is intentionally limited to low-risk workflow edits.
- Medium and high-risk actions require human approval.
- GitHub App installation flow is supported in backend services, but a production deployment still needs a public URL, webhook configuration, and installed repositories.
- AWS, Terraform, Prometheus, Kubernetes, and infrastructure automation are optional future work unless explicitly enabled.
- The system does not bypass repository review rules and should not be used to push directly to protected branches.

## Future Work

- Expand the dataset with more real CI/CD logs and labels.
- Add model versioning and experiment tracking.
- Add richer evaluation comparing manual and automated diagnosis/setup time.
- Improve GitHub App onboarding UI.
- Add automatic issue comments or PR comments for diagnosed workflow failures.
- Add safe patch generation for more failure classes.
- Add deployment guides for cloud hosting.
- Add optional infrastructure integrations for Terraform, Kubernetes, Prometheus, and AWS.

## Additional Documentation

- `docs/FINAL_DEMO.md`
- `docs/EVALUATION_PLAN.md`
- `docs/API_REFERENCE.md`
- `docs/ARCHITECTURE.md`
- `docs/DEPLOYMENT.md`
- `docs/AUDIT_LOGGING.md`
