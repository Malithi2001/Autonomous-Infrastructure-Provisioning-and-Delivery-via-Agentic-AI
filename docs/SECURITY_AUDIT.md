# Security Audit Notes

Last reviewed: 2026-06-02

This note records repository security checks for final submission. Do not paste real secret values into this file.

## Findings

- Tracked environment files: only `.env.example` templates were detected as tracked project files. Local `backend/.env` and `frontend/.env` exist for development and must stay untracked.
- Local database files: local SQLite database files were detected in the working tree. They are ignored and should not be included in submission archives.
- Secret defaults: tracked configuration uses placeholder/default development values such as the JWT secret placeholder and demo admin password. These must be replaced before any hosted deployment.
- GitHub token handling: GitHub API helpers accept token overrides and audit code redacts token-like values. Approval and shell-command paths now redact token-like values before persistence/logging.
- GitHub writes: workflow generation code creates a branch and pull request and refuses direct writes to `main` or `master`.
- Destructive actions: Docker restart/start/stop/run, workflow dispatch, and shell command execution should require HITL approval. The registry wraps these operations with approval gates.
- CORS/auth: backend CORS allows configured local frontend origins with credentials. Production deployments must restrict `ALLOWED_ORIGINS` to the exact deployed frontend URL and enable secure cookies.
- Frontend secrets: frontend code should only contain public API base URLs. Never put GitHub tokens, private keys, JWT secrets, or cloud credentials in frontend `.env` files.
- Shell execution: shell commands use an allowlist and `shell=False`, but host log access and shell output can still expose sensitive operational data.

## Manual Actions Before Deployment

1. Rotate any token or key that was ever pasted into a local `.env`, terminal, screenshot, or demo recording.
2. Replace `SECRET_KEY` and `DEFAULT_ADMIN_PASSWORD` with strong deployment-only values.
3. Set `COOKIE_SECURE=true` and use HTTPS in deployed environments.
4. Restrict `ALLOWED_ORIGINS` to the deployed frontend domain.
5. Review whether `cat /var/log/syslog` should remain in the shell allowlist for the final demo environment.
6. Confirm GitHub App permissions are least-privilege for repository contents, workflows, pull requests, actions, and metadata.
7. Confirm final ZIP excludes `.env`, local databases, logs, caches, virtualenvs, node modules, and Git metadata.
