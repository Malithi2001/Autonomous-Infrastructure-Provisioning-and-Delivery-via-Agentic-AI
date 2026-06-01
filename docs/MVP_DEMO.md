# MVP Demo Guide

This is the shorter demo path for quick reviews.

## 1. Demo Objective

Show that the project can:

- diagnose CI/CD logs,
- detect repository stack,
- generate GitHub Actions workflows,
- create workflow PRs,
- store workflow failure diagnoses,
- use approvals and audit logs.

## 2. Five-Minute Flow

### 1. Login

Show that the user enters a protected dashboard after authentication.

Point to:

- JWT auth,
- httpOnly cookie,
- RBAC-based navigation.

### 2. Diagnose A Log

Open Diagnosis.

Paste a log such as:

```text
Run npm test
npm ERR! Missing script: "test"
Error: Process completed with exit code 1.
```

Expected:

- label: `npm_missing_test_script` or similar,
- confidence,
- suggested fix,
- recommendation.

### 3. Scan Repository

Open Repository Setup.

Scan `owner/repo`.

Expected:

- file list,
- stack,
- readiness score,
- warnings,
- next actions.

### 4. Create Workflow PR

Create the workflow pull request.

Expected:

- branch name,
- `.github/workflows/ai-generated-ci.yml`,
- GitHub PR URL.

Explain that this is safe because it does not push to main.

### 5. Show Audit

Open Executions.

Show:

- repository scan record,
- workflow PR record,
- prediction record,
- webhook record if available.

## 3. Multi-Agent Explanation

Use this short version:

> The Orchestration Agent receives the user request, detects the intent, and sends it to one specialized agent. CI/CD Agent handles stack and YAML generation, Diagnosis Agent handles logs and ML prediction, GitHub Agent handles real repositories and PRs, and CLI Agent is optional for local runtime inspection.

## 4. MVP Boundaries

Be honest:

- It handles common CI/CD failure categories, not every possible build failure.
- Generated workflows must be reviewed before merging.
- Real GitHub operations depend on correct permissions.
- AWS/Terraform/Kubernetes are future work.

## 5. Best Screens To Show

- Diagnosis page.
- Repository Setup page.
- Workflow Failures page.
- Approvals page.
- Executions page.
