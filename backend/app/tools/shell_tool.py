"""
Shell Tool — Executes only pre-approved, safe shell commands.
All other commands are blocked for security.
"""
import subprocess
import shlex
import re

from app.core.logging import logger

# Strict allowlist — only these command prefixes are permitted
ALLOWED_COMMANDS = [
    "df -h", "df -H",
    "free -h", "free -m",
    "uptime",
    "ps aux",
    "netstat -tlnp",
    "ss -tlnp",
    "systemctl status",
    "journalctl -n",
    "cat /var/log/syslog",
    "echo",
    "hostname",
    "uname -a",
    "date",
    "whoami",
    "ls -la",
    "pwd",
]


_SENSITIVE_COMMAND_PATTERNS = [
    re.compile(r"(gh[pousr]_|github_pat_)[A-Za-z0-9_]+", re.IGNORECASE),
    re.compile(r"(Bearer\s+)[^\s\"']+", re.IGNORECASE),
    re.compile(
        r"(?i)((token|secret|api[_-]?key|password|credential|access[_-]?key)\s*[:=]\s*)[^\s\"']+"
    ),
]


def _redact_command_for_log(command: str) -> str:
    """Redact token-like values before writing shell commands to logs."""
    redacted = command
    for pattern in _SENSITIVE_COMMAND_PATTERNS:
        redacted = pattern.sub(lambda match: f"{match.group(1)}[REDACTED]", redacted)
    return redacted[:200]


def _is_allowed(command: str) -> bool:
    """Check if the command starts with an allowed prefix."""
    cmd_lower = command.strip().lower()
    return any(cmd_lower.startswith(allowed.lower()) for allowed in ALLOWED_COMMANDS)


def execute_safe_shell_command(command: str) -> str:
    """
    Execute a pre-approved shell command.
    Rejects any command not in the allowlist.
    """
    if not _is_allowed(command):
        logger.warning("shell.blocked", command_preview=_redact_command_for_log(command))
        return (
            f"🚫 Command blocked: '{command}'\n"
            f"Only the following commands are permitted:\n"
            + "\n".join(f"  - {c}" for c in ALLOWED_COMMANDS)
        )
    try:
        logger.info("shell.execute", command_preview=_redact_command_for_log(command))
        result = subprocess.run(
            shlex.split(command),
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout or result.stderr
        return output.strip() or "(command produced no output)"
    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds."
    except Exception as e:
        return f"Error executing command: {e}"
