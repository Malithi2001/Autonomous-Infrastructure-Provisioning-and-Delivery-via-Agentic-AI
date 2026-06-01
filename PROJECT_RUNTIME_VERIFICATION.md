# Project Runtime Verification

This document lists what should be verified before a supervisor demo or submission.

## 1. Verification Goal

The goal is to prove that the current project can run the main CI/CD automation loop:

- authenticate user,
- diagnose logs,
- scan repository,
- generate workflow,
- create workflow PR,
- process failed workflow diagnosis,
- handle approval decisions,
- show execution history.

## 2. Backend Verification

Check:

- FastAPI app imports successfully.
- Database initializes tables.
- Auth endpoints work.
- Protected endpoints reject unauthenticated requests.
- RBAC rejects insufficient roles.
- Model prediction endpoint returns label, confidence, suggested fix, and recommendation.
- Repository scan returns stack and readiness.
- Workflow PR creation returns controlled errors when GitHub permissions are missing.
- Execution records are created for major actions.

## 3. Frontend Verification

Check:

- Login page loads.
- Authenticated layout loads.
- Role-protected pages render.
- Diagnosis page handles loading, success, and error states.
- Repository Setup page displays stack, warnings, readiness, and PR result.
- Workflow Failures page lists records.
- Approvals page can decide pending records for authorized users.
- Executions page displays filtered history.

## 4. GitHub Verification

Check:

- Token or GitHub App installation has required permissions.
- Repository scan can read the target repo.
- Workflow PR branch is not `main` or `master`.
- Workflow file path is `.github/workflows/ai-generated-ci.yml`.
- Existing workflow overwrite requires explicit user choice.
- Webhook signature verification passes with the configured secret.
- Failed workflow run creates a stored diagnosis when logs are available.

## 5. ML Verification

Check:

- `failure_model.joblib` exists or configured path points to a valid artifact.
- `fix_mapping.joblib` exists or configured path points to a valid artifact.
- Empty logs are handled gracefully.
- Known sample failures map to useful labels.
- Recommendations are returned with the API response.

## 6. Approval And Audit Verification

Check:

- Risky actions create approval requests where expected.
- Approval request has action, risk level, requester, summary, and tool input.
- Rejection prevents execution.
- Approval creates an execution record.
- Audit details do not expose secrets.

## 7. Known Demo Risks

| Risk | Meaning | Demo response |
| --- | --- | --- |
| GitHub permission error | Token/App lacks contents, pull request, actions, or workflow permission. | Explain that the system fails safely and shows the exact permission issue. |
| Webhook not received | GitHub cannot reach localhost. | Use public tunnel or explain public callback requirement. |
| Model unavailable | Artifact path missing. | Show model artifact location and retrain if needed. |
| Existing workflow file | Generated workflow already exists. | Use overwrite option only when intentionally replacing it. |
| Role blocked | User lacks permission. | Switch to operator/admin or explain RBAC behavior. |

## 8. Evidence To Capture

For the final report or viva:

- screenshot of repository scan,
- screenshot of readiness report,
- screenshot of generated workflow PR,
- screenshot of failure diagnosis,
- screenshot of approval request,
- screenshot of execution history,
- model metrics report,
- short explanation of safety controls.
