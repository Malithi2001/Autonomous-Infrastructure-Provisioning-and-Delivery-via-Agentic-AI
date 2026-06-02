# Documentation Index

This directory contains the current documentation for the Smart DevOps Assistant.

## Recommended Reading Order

1. [Project README](../README.md) - project overview and scope.
2. [Architecture](ARCHITECTURE.md) - full system architecture.
3. [Agent Design](AGENT_DESIGN.md) - orchestration and specialized agents.
4. [API Reference](API_REFERENCE.md) - backend endpoints and request/response shapes.
5. [Audit Logging](AUDIT_LOGGING.md) - execution history, approvals, and safety controls.
6. [Deployment](DEPLOYMENT.md) - runtime topology and environment requirements.
7. [GitHub End-to-End Checklist](GITHUB_E2E_CHECKLIST.md) - real repository verification flow.
8. [Evaluation Plan](EVALUATION_PLAN.md) - how to evaluate the final-year project.
9. [MVP Demo](MVP_DEMO.md) - short demo flow.
10. [Final Demo](FINAL_DEMO.md) - full supervisor presentation flow.

## Supporting Root Docs

- [Startup Guide](../STARTUP_GUIDE.md)
- [Contributing Guide](../CONTRIBUTING.md)
- [Runtime Verification](../PROJECT_RUNTIME_VERIFICATION.md)
- [Project Status](../SETUP_COMPLETE.md)
- [Architecture Quick Reference](../ARCHITECTURE_README.md)

## Main Code Areas

```text
backend/app/agents/       Multi-agent orchestration and specialized agents
backend/app/api/routes/   FastAPI route modules
backend/app/services/     Business logic services
backend/app/tools/        External integrations
backend/app/ml/           Dataset, trained model, training script, reports
frontend/src/pages/       Demo and operator screens
frontend/src/services/    Frontend API client
```

## Documentation Rules

- Keep docs aligned with code.
- Do not document secrets or real tokens.
- Mark future work clearly.
- Prefer architecture diagrams and exact endpoint paths.
- Avoid claiming production autonomy where the system still requires review.
