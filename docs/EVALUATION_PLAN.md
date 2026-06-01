# Evaluation Plan

This document defines how to evaluate the final-year project in a clear and supervisor-friendly way.

## 1. Evaluation Objectives

The evaluation should prove that the system:

- reduces manual CI/CD setup effort,
- classifies common CI/CD failures from logs,
- generates useful GitHub Actions workflows,
- safely proposes repository changes through pull requests,
- uses human approval for risky actions,
- records an audit trail,
- provides a usable frontend demo.

## 2. Research Questions

1. Can the trained model classify common CI/CD failure logs into useful categories?
2. Can repository analysis detect the stack and generate an appropriate workflow?
3. Can GitHub integration create workflow pull requests without direct branch pushes?
4. Can webhook-triggered diagnosis store useful workflow failure records?
5. Can approval and audit controls make automation safer and explainable?

## 3. Functional Evaluation Matrix

| Capability | Expected result | Evidence |
| --- | --- | --- |
| Login and RBAC | User can log in and see pages allowed by role. | Auth UI and `/auth/me`. |
| Pasted log diagnosis | Model returns label, confidence, fix, recommendation. | Diagnosis page and audit record. |
| Repository scan | Stack, detected projects, warnings, readiness report. | Repository setup page. |
| Workflow generation | Valid GitHub Actions YAML generated. | YAML preview or PR. |
| Workflow PR creation | New branch and PR opened. | GitHub PR URL and execution record. |
| Webhook failure diagnosis | Failed workflow creates `WorkflowFailure`. | Workflow failures page. |
| Fix PR request | Supported failure creates PR or approval request. | PR URL or approval page. |
| Approval decision | Approval/rejection updates execution history. | Approvals and executions pages. |
| Audit visibility | Actions are visible with source/status/tool. | Executions page. |

## 4. ML Evaluation

Evaluate the failure classifier using the dataset under `backend/app/ml/`.

Recommended metrics:

- accuracy,
- precision,
- recall,
- F1-score,
- confusion matrix,
- class-level support.

Important qualitative checks:

- Does the predicted label match the visible error?
- Is the suggested fix understandable?
- Does unknown or weak input fail gracefully?
- Are empty logs handled safely?

Recommended failure labels to test:

- `npm_missing_test_script`
- `npm_missing_lockfile`
- `npm_install_failed`
- `npm_build_failed`
- `python_missing_dependency`
- `pytest_not_found`
- `module_not_found`
- `maven_test_failed`
- `docker_build_failed`
- `wrong_runtime_version`
- `unknown_failure`

## 5. Repository Analysis Evaluation

Use small sample repositories or file lists representing:

- React/Node project with lockfile,
- Node project without test script,
- Python/FastAPI project,
- Python project without tests,
- Java Maven project,
- Docker-based project,
- monorepo with frontend and backend folders,
- repository with existing GitHub Actions workflows.

For each repository, record:

- detected language,
- framework,
- package manager,
- project directory,
- detected projects,
- warnings,
- readiness score,
- generated workflow type.

## 6. GitHub Integration Evaluation

Check these GitHub behaviors:

- repository tree fetch works,
- private or installed repositories use the expected credential path,
- workflow PR branch is not `main` or `master`,
- workflow file path is `.github/workflows/ai-generated-ci.yml`,
- overwrite is blocked unless explicitly requested,
- PR body explains detected stack and warnings,
- insufficient permissions return understandable errors.

## 7. Webhook Evaluation

For a failed workflow run, verify:

- webhook is received,
- signature verification works when secret is configured,
- unsupported events are ignored safely,
- failed workflow logs are downloaded when credentials allow it,
- prediction runs on real log text,
- `WorkflowFailure` record is created,
- execution record source is `webhook`,
- frontend lists the failure.

## 8. Safety Evaluation

Safety checks:

- no direct push to protected branches,
- no token values in execution details,
- high-risk actions create approvals,
- rejected approvals do not execute action,
- expired approvals cannot be executed,
- unauthorized roles receive `403`,
- unauthenticated requests receive `401`.

## 9. Usability Evaluation

Suggested user tasks:

1. Log in.
2. Diagnose a pasted CI/CD log.
3. Scan a GitHub repository.
4. View readiness report.
5. Create workflow PR.
6. Trigger a failed workflow and view diagnosis.
7. Review or reject an approval.
8. Inspect execution history.

Collect:

- completion success,
- time taken,
- confusing UI points,
- whether PR/recommendation was understandable,
- whether audit trail was clear.

## 10. Limitations To Report Honestly

- The model is trained on a limited curated dataset.
- It classifies common failure categories, not every possible CI/CD problem.
- Generated workflows are safe defaults and still require human review.
- GitHub permissions and repository settings can block PR/file operations.
- Webhook testing needs a public callback URL.
- AWS, Terraform, Kubernetes, and production monitoring are future work.

## 11. Final Evaluation Output

The final report can summarize:

- ML metrics from the training report,
- number of tested repository types,
- successful PR creation evidence,
- webhook diagnosis screenshot,
- approval/audit screenshot,
- known limitations and future improvements.
