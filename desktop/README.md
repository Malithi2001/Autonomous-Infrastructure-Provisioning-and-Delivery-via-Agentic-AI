# Smart DevOps Assistant Desktop

This folder contains the Electron shell for packaging the Smart DevOps Assistant as a local desktop app.

Desktop mode is intended for local single-user demos, especially on Windows. It opens directly as `Desktop User`, bypasses JWT/RBAC, hides Users & Roles and Sign out, and still keeps approval gates and audit logging.

## Easy Windows Setup

Open PowerShell in the project folder and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\desktop\setup-windows.ps1
```

The script installs dependencies, builds the frontend, packages the backend executable, and creates an installer in:

```text
desktop\dist
```

Run the generated `Smart DevOps Assistant Setup ...exe`, then open the app from the Start Menu or desktop shortcut.

## Run Without Installer

After setup, run the desktop app directly from source:

```powershell
.\desktop\run-desktop.ps1
```

For development from the repository root:

```bash
make desktop-dev
```

This starts:

- backend on `http://127.0.0.1:8000`,
- Vite frontend on `http://127.0.0.1:5173`,
- Electron pointed at the Vite dev server.

## Manual Build Commands

From the repository root:

```bash
make setup
make build-frontend
make build-backend-exe
make desktop-check
make desktop-build-win
```

`make desktop-check` verifies the backend import, frontend build, Electron config, model artifact, environment templates, and that no real `.env` file is present in desktop build output.

## Desktop Environment

Backend:

```text
DESKTOP_MODE=true
DISABLE_AUTH=true
HOST=127.0.0.1
PORT=8000
```

Frontend:

```text
VITE_DESKTOP_MODE=true
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Keep GitHub tokens and GitHub App private keys in backend environment variables only. Do not store them in frontend files or desktop packaged output.

## Optional Tools

Docker features require Docker Desktop to be running on the same machine.

GitHub repository actions require either:

- `GITHUB_TOKEN` for local PAT fallback, or
- GitHub App values such as `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, and webhook secret values.

GitHub webhooks require a public HTTPS URL. A desktop app running on localhost cannot receive GitHub webhooks directly without a tunnel such as ngrok.
