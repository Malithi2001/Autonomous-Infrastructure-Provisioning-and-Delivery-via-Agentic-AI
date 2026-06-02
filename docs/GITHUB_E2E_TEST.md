# Real GitHub End-to-End Test Guide

This guide explains how to verify the real GitHub automation flow before the final demo. It is designed for a safe demo repository, not for production repositories.

## Demo Repository Setup

Use a small repository that you control.

Recommended setup:

- Create a new GitHub repository such as `your-user/devops-assistant-demo`.
- Add a minimal app, for example a Python, Node.js, or static project.
- Add at least one intentionally failing test or workflow condition for diagnosis testing.
- Install the GitHub App on this repository, or configure a fine-grained PAT for local MVP testing.
- Confirm the repository full name matches `owner/repo` format.

The backend should use that repository name through `GITHUB_REPO_FULL_NAME`.

## Environment Variables

The system supports two GitHub authentication modes:

- GitHub App installation token for production-style repository access.
- `GITHUB_TOKEN` personal access token fallback for local development.

Required for GitHub App mode:

```text
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY=
GITHUB_APP_WEBHOOK_SECRET=
GITHUB_APP_CLIENT_ID=
GITHUB_APP_CLIENT_SECRET=
GITHUB_REPO_FULL_NAME=owner/repo
```

Optional local fallback:

```text
GITHUB_TOKEN=
GITHUB_REPO_FULL_NAME=owner/repo
```

Webhook verification should use the same secret in GitHub and the backend. Do not paste tokens into frontend files.

## Public Tunnel Setup

GitHub cannot deliver webhooks to `localhost`, so expose the backend through a public HTTPS tunnel.

Typical local tunnel flow:

```bash
ngrok http 8000
```

Use the generated HTTPS URL as the public backend base URL. The webhook endpoint should look like:

```text
https://<public-backend-domain>/api/v1/webhooks/github
```

If your environment supports it, store the public base URL using one of:

```text
PUBLIC_BACKEND_URL=
BACKEND_PUBLIC_URL=
NGROK_DOMAIN=
WEBHOOK_BASE_URL=
```

## Webhook Setup

In the GitHub App or repository webhook settings:

- Set Payload URL to `https://<public-backend-domain>/api/v1/webhooks/github`.
- Set Content type to `application/json`.
- Set Secret to the backend webhook secret.
- Enable workflow-related events, especially workflow run events.
- Keep the webhook active.

After saving, GitHub should show successful delivery attempts once events occur.

## Testing Steps

1. Run the local checklist:

```bash
make github-e2e-checklist
```

2. Start the backend and frontend using the project developer commands.

3. Log in to the frontend.

4. Scan the demo repository from the repository page.

Expected backend endpoint:

```text
POST /api/v1/repositories/scan
```

5. Generate a GitHub Actions workflow and create a workflow PR.

Expected backend endpoint:

```text
POST /api/v1/repositories/create-workflow-pr
```

6. Open GitHub and confirm the PR was created from an `ai-cicd/...` branch.

7. Review and merge the workflow PR in GitHub.

8. Trigger a failing workflow run in the demo repository.

9. Confirm GitHub sends the webhook to the backend.

10. Open the Workflow Failures page and confirm the system shows diagnosis output.

11. Open the Audit page and confirm key events were recorded.

12. Test the approval flow for a fix PR if the diagnosed failure supports an automated fix.

## Expected Results

The full flow is considered demo-ready when:

- The repository scan succeeds.
- A workflow PR is created without direct pushes to the default branch.
- A failed GitHub Actions run is delivered through the webhook.
- Real workflow logs are downloaded when credentials allow it.
- The failure model predicts a failure class.
- A suggested fix is shown.
- High-risk fix PR actions wait for approval.
- Approved fix PR actions use a GitHub App installation token when available.
- Audit logs show repository, GitHub, approval, diagnosis, and PR activity.

## Troubleshooting

`Webhook URL is not reachable`

Use a public HTTPS tunnel. GitHub cannot call `localhost`.

`401 Unauthorized`

Check backend authentication first. Log in again and confirm cookies are being sent from the frontend to the backend.

`invalid GitHub token`

Confirm `GITHUB_TOKEN` is present for local fallback, or confirm the GitHub App is installed on the demo repository.

`insufficient GitHub permissions`

For PR creation and workflow file changes, the GitHub App or PAT needs repository contents and workflows write access. Pull request access is also needed for PR creation.

`Dependency review is not supported`

Dependency review requires GitHub dependency graph support. The workflow generator should avoid requiring dependency review for repositories where it is unsupported.

`No workflow failure appears in the frontend`

Check GitHub webhook delivery logs, backend logs, webhook secret configuration, and whether the failed workflow event type is supported.

`Approval is created but no PR appears after approval`

Check that the approval dispatcher can resolve the repository installation. If no installation exists, confirm the local PAT fallback is configured.
