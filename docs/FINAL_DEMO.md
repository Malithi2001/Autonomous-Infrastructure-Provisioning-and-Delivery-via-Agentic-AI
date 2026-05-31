# Final Demo Script

This script is designed for a supervisor demo of the final-year project:

`Agentic AI-Powered Smart DevOps Assistant for Autonomous Software Delivery and Infrastructure Management`

## Demo Goal

Show that the system can:

- classify CI/CD failure logs using a trained model,
- generate GitHub Actions workflows from repository structure,
- scan GitHub repositories,
- create workflow setup pull requests,
- store workflow failure diagnosis results,
- recommend safe fixes,
- create fix PRs with approval where required,
- record actions in the audit log.

## Demo Repository Requirements

Use a small GitHub repository that is safe to modify during the demo.

Recommended repository contents:

```text
package.json
package-lock.json
src/App.jsx
vite.config.js
Dockerfile
```

Recommended repository settings:

- The repository is accessible by the configured `GITHUB_TOKEN` or installed GitHub App.
- The token/app has Contents read/write, Pull requests read/write, Actions read.
- The repository allows pull requests from branches created by the token/app.
- Do not use a production repository.
- Do not use real secrets in files or workflow logs.

Optional workflow file for fix PR demo:

```yaml
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm ci
      - run: npm test
```

## Final Demo Command List

Prepare environment:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Train model:

```bash
cd backend
venv/bin/python app/ml/train_failure_model.py
```

Start backend:

```bash
cd backend
venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Start frontend:

```bash
cd frontend
npm run dev
```

Alternative Docker startup:

```bash
docker compose up -d --build
```

Open:

```text
http://localhost:5173
```

Demo login:

```text
Email: operator@devops.example.com
Password: operator123
```

## Step 1: Introduce the Project

Say:

This project is an Agentic AI-Powered Smart DevOps Assistant. It reduces manual CI/CD troubleshooting by combining a trained failure classification model, repository analysis, GitHub Actions workflow generation, GitHub pull request automation, human approval, and audit logging.

Show:

- README project title and system overview.
- Frontend dashboard navigation.

## Step 2: Train the Model

Run:

```bash
cd backend
venv/bin/python app/ml/train_failure_model.py
```

Show:

- Accuracy, precision, recall, F1-score.
- `backend/app/ml/reports/metrics.json`
- `backend/app/ml/reports/classification_report.txt`
- `backend/app/ml/reports/confusion_matrix.png`

Explain:

- Logs are converted using TF-IDF.
- Logistic Regression predicts the failure label.
- The fix mapping returns a suggested remediation.

## Step 3: Failure Classification Demo

Open:

```text
CI/CD Assistant
```

Paste sample log:

```text
npm ERR! Missing script: "test"
npm ERR!
npm ERR! To see a list of scripts, run:
npm ERR!   npm run
Error: Process completed with exit code 1.
```

Click:

```text
Predict Failure
```

Expected prediction:

```text
label: npm_missing_test_script
suggested fix: Add a test script or update the workflow to use npm test --if-present.
```

Explain:

The model identifies the likely root cause from the log text and returns both a classification label and practical fix guidance.

## Step 4: More Sample CI/CD Failure Logs

Missing npm lockfile:

```text
Run npm ci
npm ERR! The npm ci command can only install with an existing package-lock.json.
npm ERR! Missing package-lock.json.
Error: Process completed with exit code 1.
```

Expected prediction:

```text
npm_missing_lockfile
```

Pytest missing:

```text
Run pytest
/bin/bash: line 1: pytest: command not found
Error: Process completed with exit code 127.
```

Expected prediction:

```text
pytest_not_found
```

Python dependency missing:

```text
ModuleNotFoundError: No module named 'fastapi'
Error: Process completed with exit code 1.
```

Expected prediction:

```text
python_missing_dependency
```

Docker build failed:

```text
Run docker build -t demo-app .
failed to solve: failed to read dockerfile: open Dockerfile: no such file or directory
Error: Process completed with exit code 1.
```

Expected prediction:

```text
docker_build_failed
```

Wrong runtime:

```text
The engine "node" is incompatible with this module. Expected version ">=20".
Got "16.20.0".
Error: Process completed with exit code 1.
```

Expected prediction:

```text
wrong_runtime_version
```

## Step 5: Workflow Generator Demo

On the CI/CD Assistant page, enter:

```text
package.json
package-lock.json
src/App.jsx
vite.config.js
Dockerfile
```

Click:

```text
Generate Workflow
```

Show:

- Detected stack: JavaScript / React / npm / Docker.
- Recommended workflow: `node-ci`.
- Generated YAML.
- Path: `.github/workflows/ai-generated-ci.yml`.

Explain:

This is deterministic workflow generation based on repository signals, not a random LLM response.

## Step 6: Repository Scan Demo

Open:

```text
Repository Setup
```

Enter:

```text
owner/repo
```

Click:

```text
Scan Repository
```

Show:

- Repository name.
- Detected stack.
- Recommended workflow.
- File count.

Explain:

The backend fetches the repository tree through GitHub and runs the repository analyzer on real file paths.

## Step 7: Workflow PR Demo

Click:

```text
Create Workflow PR
```

Show:

- Created branch, for example `ai-cicd/setup-pipeline`.
- Workflow path `.github/workflows/ai-generated-ci.yml`.
- Pull request URL.

Open the PR in GitHub and explain:

- The system creates a new branch.
- It does not push directly to `main` or `master`.
- A human can review and merge the workflow.

## Step 8: Failure Diagnosis Demo

Trigger or simulate a failed GitHub Actions workflow.

Expected backend flow:

1. GitHub sends a `workflow_run` webhook.
2. Backend checks action is `completed`.
3. Backend checks conclusion is `failure`.
4. Backend downloads real workflow logs.
5. Logs are cleaned and redacted.
6. Model predicts failure label and confidence.
7. Recommendation is generated.
8. Diagnosis is stored as a workflow failure record.
9. Audit entries are created.

Open:

```text
Workflow Failures
```

Show:

- Repository.
- Workflow name.
- Branch.
- Run ID.
- Predicted label.
- Confidence.
- Suggested fix.
- Workflow URL.
- Status.
- Log excerpt.

## Step 9: Fix PR Demo

On Workflow Failures, expand a diagnosed failure.

If the label is supported for safe fixes, click:

```text
Create Fix PR
```

Supported first safe fixes:

- `npm_missing_test_script`: change `npm test` to `npm test --if-present`.
- `npm_missing_lockfile`: change `npm ci` to `npm install` when safe.
- `pytest_not_found`: install pytest before running pytest.

Show:

- Fix branch, for example `ai-cicd/fix-{run_id}`.
- Fix PR URL.
- PR body explaining the failure and safety notes.

Explain:

Only low-risk workflow edits are applied automatically. If the system is uncertain, it returns recommendation-only.

## Step 10: Approval Demo

For medium/high-risk actions, the system creates an approval request instead of creating a PR immediately.

Open:

```text
Approvals
```

Show approval details:

- Repository.
- Workflow run.
- Predicted failure.
- Suggested fix.
- Proposed file changes.
- Risk level.

Click:

```text
Approve
```

Then show:

- The fix PR is created after approval.
- Rejection updates the workflow failure status to rejected.

Explain:

This keeps automation supervised and suitable for safe DevOps workflows.

## Step 11: Audit Log Demo

Open:

```text
Audit
```

Show recent records for:

- model prediction,
- repository scan,
- workflow generation,
- workflow PR creation,
- workflow failure webhook,
- log download,
- fix recommendation,
- fix PR creation,
- approval decision.

Explain:

Every important agent/GitHub/model action is stored as an execution/audit record with action summary, tool name, status, actor, input summary, output summary, and timestamp.

## Step 12: Closing Summary

Close with:

The MVP demonstrates a safe CI/CD automation assistant. It does not replace developers or DevOps engineers. Instead, it reduces repetitive diagnosis/setup work, opens reviewable pull requests, uses human approval for risky actions, and keeps an audit trail for accountability.

## Demo Troubleshooting

Backend not reachable:

```bash
cd backend
venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend points to wrong API:

```bash
cat frontend/.env
```

Expected:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Model missing:

```bash
cd backend
venv/bin/python app/ml/train_failure_model.py
```

GitHub PR fails:

- Check `GITHUB_TOKEN` or GitHub App installation.
- Check token permissions.
- Check repository full name.
- Check branch protection and repository access.
