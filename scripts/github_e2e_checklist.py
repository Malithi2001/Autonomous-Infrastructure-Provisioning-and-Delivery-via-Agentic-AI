#!/usr/bin/env python3
"""Print a safe GitHub end-to-end demo checklist.

The script does not call the GitHub API or the local backend. It only checks
whether expected environment variable names are present in the current process
or backend/.env, and it never prints secret values.
"""
from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ENV = ROOT / "backend" / ".env"


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


FILE_ENV = _read_env_file(BACKEND_ENV)


def configured(key: str) -> bool:
    return bool(os.environ.get(key) or FILE_ENV.get(key))


def status(value: bool) -> str:
    return "[OK]" if value else "[TODO]"


def config_line(label: str, keys: list[str]) -> str:
    present = any(configured(key) for key in keys)
    joined = " or ".join(keys)
    return f"{status(present)} {label}: {joined}"


def main() -> None:
    has_pat = configured("GITHUB_TOKEN")
    has_app = all(
        configured(key)
        for key in (
            "GITHUB_APP_ID",
            "GITHUB_APP_PRIVATE_KEY",
            "GITHUB_APP_WEBHOOK_SECRET",
        )
    )
    has_repo = configured("GITHUB_REPO_FULL_NAME")
    has_webhook_secret = configured("GITHUB_APP_WEBHOOK_SECRET") or configured("GITHUB_WEBHOOK_SECRET")
    has_public_url = any(
        configured(key)
        for key in (
            "PUBLIC_BACKEND_URL",
            "BACKEND_PUBLIC_URL",
            "NGROK_DOMAIN",
            "WEBHOOK_BASE_URL",
        )
    )

    print("GitHub End-to-End Demo Checklist")
    print("=" * 35)
    print("This helper does not call GitHub or your backend. Secret values are hidden.")
    print()
    print("Detected configuration")
    print(config_line("GitHub PAT fallback", ["GITHUB_TOKEN"]))
    print(config_line("GitHub App ID", ["GITHUB_APP_ID"]))
    print(config_line("GitHub App private key", ["GITHUB_APP_PRIVATE_KEY"]))
    print(config_line("Webhook secret", ["GITHUB_APP_WEBHOOK_SECRET", "GITHUB_WEBHOOK_SECRET"]))
    print(config_line("Demo repository", ["GITHUB_REPO_FULL_NAME"]))
    print(config_line("Public backend/tunnel URL", ["PUBLIC_BACKEND_URL", "BACKEND_PUBLIC_URL", "NGROK_DOMAIN"]))
    print()
    print("Manual checklist")
    steps = [
        (
            has_pat or has_app,
            "Check GITHUB_TOKEN or GitHub App env vars are configured.",
        ),
        (
            has_webhook_secret,
            "Check webhook secret is configured in GitHub and backend/.env.",
        ),
        (
            has_public_url,
            "Check ngrok/public tunnel points to backend port 8000.",
        ),
        (
            has_repo,
            "Check demo repo exists and matches GITHUB_REPO_FULL_NAME.",
        ),
        (
            False,
            "Check repo scan endpoint: POST /api/v1/repositories/scan.",
        ),
        (
            False,
            "Check create workflow PR endpoint: POST /api/v1/repositories/create-workflow-pr.",
        ),
        (
            False,
            "Check GitHub PR was created from an ai-cicd branch.",
        ),
        (
            False,
            "Check workflow PR was reviewed and merged in the demo repo.",
        ),
        (
            False,
            "Check a failed workflow run was triggered.",
        ),
        (
            False,
            "Check webhook received the workflow_run failure event.",
        ),
        (
            False,
            "Check Workflow Failures page shows diagnosis.",
        ),
        (
            False,
            "Check Audit page shows scan, approval, PR, webhook, and diagnosis records.",
        ),
        (
            False,
            "Check approval/fix PR flow for a diagnosed failure.",
        ),
    ]

    for index, (done, text) in enumerate(steps, start=1):
        print(f"{index:02d}. {status(done)} {text}")

    print()
    print("Recommended webhook URL shape:")
    print("  https://<public-backend-domain>/api/v1/webhooks/github")
    print()
    print("Full guide:")
    print("  docs/GITHUB_E2E_TEST.md")


if __name__ == "__main__":
    main()
