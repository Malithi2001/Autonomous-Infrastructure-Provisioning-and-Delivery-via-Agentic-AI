# MVP Demo Guide

Use this guide for a short supervisor demo of the CI/CD failure diagnosis and workflow generation MVP.

## 1. Train the Failure Prediction Model

From the project root:

```bash
cd backend
venv/bin/python app/ml/train_failure_model.py
```

Show that the script prints accuracy/classification metrics and saves:

- `backend/app/ml/failure_model.joblib`
- `backend/app/ml/fix_mapping.joblib`

Explain:

- The model uses TF-IDF features over CI/CD log text.
- Logistic regression predicts the likely failure category.
- A saved fix mapping returns a human-readable remediation suggestion.

## 2. Start the App

Terminal 1:

```bash
make dev-backend
```

Terminal 2:

```bash
make dev-frontend
```

Open:

```text
http://localhost:5173
```

If the frontend cannot reach the API, check `frontend/.env` and make sure `VITE_API_BASE_URL` matches the backend port.

Demo login:

```text
Email: viewer@company.example.com
Password: viewer123
```

Then open:

```text
http://localhost:5173/diagnosis
```

## 3. Paste a Failed CI/CD Log

On the CI/CD Assistant page, use the Failure Log Classifier section.

Example log:

```text
npm test failed: npm ERR! Missing script: test.
To see a list of scripts, run npm run.
```

Click:

```text
Predict Failure
```

## 4. Show the Prediction

Point out the three returned values:

- Label, for example `npm_missing_test_script`
- Confidence score
- Suggested fix, for example adding a `test` script to `package.json` or updating the CI command

Explain that this gives a developer a quick root-cause hint instead of manually reading long logs.

## 5. Enter a Repository File List

Use the Workflow Generator section.

Example file list:

```text
package.json
package-lock.json
src/App.tsx
vite.config.ts
Dockerfile
```

Click:

```text
Generate Workflow
```

## 6. Generate a GitHub Actions Workflow

Show:

- detected stack, for example JavaScript / React / npm / Docker,
- recommended workflow type, for example `node-ci`,
- generated YAML in the code block,
- output path `.github/workflows/ai-generated-ci.yml`.

Explain that the current MVP generates workflow YAML deterministically from repository signals.

## 7. Optional API Demo

Prediction endpoint:

```bash
curl -i -sS -c /tmp/devops_demo_cookie.txt \
  -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"viewer@company.example.com","password":"viewer123"}'

curl -i -sS -b /tmp/devops_demo_cookie.txt \
  -X POST http://127.0.0.1:8000/api/v1/model/predict-failure \
  -H "Content-Type: application/json" \
  -d '{"log_text":"npm test failed: npm ERR! Missing script: test."}'
```

Workflow generation endpoint:

```bash
curl -i -sS \
  -X POST http://127.0.0.1:8000/api/v1/cicd/generate-workflow \
  -H "Content-Type: application/json" \
  -d '{"files":["package.json","package-lock.json","src/App.tsx","vite.config.ts","Dockerfile"]}'
```

## 8. Future GitHub App PR Automation

Explain the planned production workflow:

1. A GitHub App receives a failed workflow event.
2. The backend fetches the workflow logs.
3. The trained model predicts the failure category.
4. The repo analyzer detects the stack.
5. The workflow generator creates or updates GitHub Actions YAML.
6. A GitHub branch is created.
7. The generated workflow is committed to `.github/workflows/ai-generated-ci.yml`.
8. A pull request is opened for a human reviewer.

The repository already includes GitHub helper code for creating workflow PRs; the future work is to connect that into a complete GitHub App installation and approval flow.

## 9. Demo Close

Summarize the MVP value:

- faster CI/CD failure diagnosis,
- practical fix suggestions,
- automated CI workflow generation,
- clear path to supervised PR automation instead of uncontrolled production changes.
