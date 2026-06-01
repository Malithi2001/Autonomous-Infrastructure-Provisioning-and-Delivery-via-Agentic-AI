# AGENTS.md

Guidance for future Codex work in this repository.

## 1. Project Overview

Project title:
**Agentic AI-Powered Smart DevOps Assistant for Autonomous Software Delivery and Infrastructure Management**

This project is a web-based CI/CD automation assistant. It combines a FastAPI backend, React frontend, trained ML model, GitHub Actions workflow generation, GitHub webhook handling, human-in-the-loop approval, and audit logging.

The system should help users:

- Classify failed CI/CD logs.
- Recommend practical fixes.
- Detect repository stack from file lists or GitHub repository data.
- Generate GitHub Actions workflow YAML.
- Receive GitHub webhook events for failed workflows.
- Download real GitHub Actions logs.
- Diagnose failures with the trained model.
- Create pull requests for generated workflows and safe fixes.
- Require human approval before high-risk automation.
- Keep an audit trail of important actions.

## 2. Main Implementation Goal

Build and maintain a supervisor-demo-ready MVP that proves the CI/CD automation loop:

1. A user logs in.
2. The user tests failure diagnosis from CI/CD logs.
3. The user generates a GitHub Actions workflow from repository files.
4. GitHub webhook events can trigger failure diagnosis.
5. Real GitHub Actions logs are downloaded when available.
6. The model predicts the failure type and suggests a fix.
7. Generated workflows or safe fixes are proposed through a pull request.
8. High-risk actions wait for human approval.
9. Agent, GitHub, model, approval, and execution actions are audit logged where possible.

Keep AWS, Terraform, Prometheus, and Kubernetes as optional future work unless the user explicitly requests them.

## 3. Tech Stack

Backend:

- FastAPI
- SQLAlchemy async ORM
- PostgreSQL or Supabase-compatible PostgreSQL
- JWT auth with httpOnly cookies
- Role-based access control
- LangChain-based DevOps agent
- scikit-learn failure classifier
- PyGithub for GitHub API work
- Celery and Redis where background work is needed
- pytest, pytest-asyncio, flake8, mypy

Frontend:

- React
- Vite
- TypeScript
- Tailwind CSS
- Radix UI primitives
- lucide-react icons
- Zustand stores
- Axios API client
- react-router-dom routing

ML:

- TF-IDF text features
- LogisticRegression classifier
- joblib model artifacts
- CSV training dataset

## 4. Backend Coding Rules

- Put API routes in `backend/app/api/routes/`.
- Put business logic in `backend/app/services/`.
- Put agent-callable integrations in `backend/app/tools/`.
- Put ORM models in `backend/app/models/models.py`.
- Put Pydantic schemas in `backend/app/schemas/schemas.py`.
- Put shared config, security, database, and logging code in `backend/app/core/`.
- Use async database access with `AsyncSession`.
- Use SQLAlchemy ORM or SQLAlchemy expressions, not string-built SQL.
- Use existing `require_permission(...)` dependencies for protected endpoints.
- Return Pydantic response models for stable API contracts.
- Use structured logging through the existing logger.
- Keep route handlers thin; move workflow logic into services.
- Do not break existing endpoints unless the user explicitly asks for a breaking change.

Backend security rules:

- Do not hardcode secrets, database URLs, GitHub tokens, API keys, or passwords.
- Do not log secrets or raw auth headers.
- Verify GitHub webhook signatures when a webhook secret is configured.
- Validate user input before using it in GitHub, database, shell, Docker, or agent tools.
- Keep privileged actions behind RBAC and approval gates.

## 5. Frontend Coding Rules

- Put pages in `frontend/src/pages/`.
- Put reusable components in `frontend/src/components/`.
- Put feature-specific API calls in `frontend/src/services/api.ts` unless the file becomes too large, then split by domain.
- Put shared types in `frontend/src/types/`.
- Use existing layout, cards, buttons, input styles, icons, and Tailwind conventions.
- Use Zustand for global app state.
- Keep page UI demo-friendly and easy to explain.
- Handle loading, empty, success, and error states.
- Never expose secrets in frontend code or `.env` files.
- Do not store GitHub tokens in browser state or localStorage.
- Do not add large new UI frameworks unless explicitly requested.

Frontend routing rules:

- Add new pages to the existing React Router structure.
- Add navigation only when it fits the current sidebar/navbar pattern.
- Respect RBAC visibility rules in the frontend, but never rely on frontend checks as the only security layer.

## 6. ML Model Rules

- Keep model code under `backend/app/ml/` and `backend/app/services/failure_prediction_service.py`.
- Keep the MVP model simple unless the user requests model research work.
- Use `dataset.csv` as the training source.
- Save model artifacts with joblib.
- Return at least:
  - `label`
  - `confidence`
  - `suggested_fix`
- Handle empty logs gracefully.
- Lazy-load model artifacts once and reuse them.
- Do not retrain during API prediction requests.
- Do not hardcode the full label-to-fix mapping in route code; use the trained artifact or a dedicated service mapping.
- If model behavior changes, update tests and documentation.

## 7. GitHub Integration Safety Rules

- Never push directly to `main` or `master`.
- All GitHub repository modifications must happen through:
  1. A new branch.
  2. One or more commits on that branch.
  3. A pull request.
- Do not force-push.
- Do not merge pull requests automatically.
- Do not delete branches unless explicitly requested and approved.
- Do not hardcode GitHub tokens.
- Prefer GitHub App installation tokens for production-style flows.
- If a personal access token is used for local MVP testing, load it only from environment variables.
- Log GitHub actions without logging token values.
- Make branch names descriptive, for example `ai-cicd/generated-workflow` or `ai-fix/npm-test-script`.
- Include enough PR description for a human reviewer to understand what changed and why.

GitHub webhook rules:

- Verify `X-Hub-Signature-256` when a webhook secret exists.
- Ignore unsupported webhook events safely.
- For failed workflow runs, fetch the real logs before model diagnosis when credentials allow it.
- Store or audit useful metadata such as repository, workflow name, run id, conclusion, prediction label, and PR URL.

## 8. Human Approval Rules

High-risk actions must require human approval before execution.

High-risk examples:

- Creating a pull request that modifies workflows or source files.
- Applying an automated fix to a repository.
- Running shell, Docker, deployment, or infrastructure-changing commands.
- Changing user roles or permissions.
- Deleting files, branches, or resources.
- Modifying CI/CD behavior in a real repository.

Low-risk examples:

- Reading logs.
- Predicting a failure from pasted text.
- Generating workflow YAML without committing it.
- Listing recent executions.
- Viewing pending approvals.

Approval requirements:

- Create an approval request before high-risk execution.
- Include action, risk level, summary, requester, tool name, and tool input where possible.
- Allow an operator or admin to approve or reject.
- If rejected, do not execute the action.
- If expired, do not execute the action.
- Never auto-approve high-risk actions.

## 9. Audit Logging Rules

Audit log where possible:

- User login/logout and permission failures.
- Agent chat actions and tool calls.
- Failure prediction requests and outcomes.
- Workflow generation requests and detected stack.
- GitHub webhook events.
- GitHub log download attempts.
- Pull request creation attempts.
- Approval request creation and decisions.
- Executions, failures, and cancellations.

Use existing execution/audit models and services before adding new tables. If richer CI/CD audit records are needed, add focused models and tests.

Never log:

- Passwords.
- JWTs.
- Refresh tokens.
- GitHub tokens.
- API keys.
- Full secret-bearing environment variables.

## 10. Testing Commands

Backend setup:

```bash
make setup-backend
```

Run backend tests:

```bash
make test-backend
```

Run backend lint/type checks:

```bash
make lint-backend
```

Train the failure model:

```bash
cd backend && venv/bin/python app/ml/train_failure_model.py
```

Run backend locally:

```bash
make dev-backend
```

Frontend setup:

```bash
make setup-frontend
```

Run frontend lint:

```bash
make lint-frontend
```

Build frontend:

```bash
make build-frontend
```

Run frontend locally:

```bash
make dev-frontend
```

Full stack with Docker Compose:

```bash
make dev
```

If a command is unavailable because dependencies are missing, install dependencies using the project setup commands instead of inventing a new dependency flow.

## 11. Things Codex Must Not Do

- Do not remove existing working features.
- Do not overwrite user changes without checking the diff.
- Do not hardcode secrets, GitHub tokens, API keys, passwords, or database URLs.
- Do not print or expose secret values from `.env` files.
- Do not push directly to `main` or `master`.
- Do not force-push.
- Do not auto-merge pull requests.
- Do not bypass human approval for high-risk actions.
- Do not make direct production infrastructure changes.
- Do not add AWS, Terraform, Prometheus, or Kubernetes work unless explicitly requested.
- Do not replace the existing backend/frontend stack with another framework.
- Do not add unrelated refactors while fixing a focused issue.
- Do not silently ignore failing tests.
- Do not claim tests passed unless they were actually run.
- Do not make networked GitHub repository changes unless the user asked for that specific action.
- Do not use real user/customer/private data for model training.
- Do not weaken auth, RBAC, webhook verification, or approval checks to make a demo easier.
