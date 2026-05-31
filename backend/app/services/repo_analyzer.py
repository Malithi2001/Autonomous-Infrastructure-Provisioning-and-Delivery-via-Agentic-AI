"""Pure repository stack detection for CI/CD workflow recommendations."""
from __future__ import annotations

from typing import Literal, TypedDict


RecommendedWorkflow = Literal["node-ci", "python-ci", "java-ci", "docker-ci", "generic-ci"]


class StackDetection(TypedDict):
    language: str
    framework: str
    package_manager: str
    has_docker: bool
    has_existing_workflows: bool
    recommended_workflow: RecommendedWorkflow


def detect_stack(files: list[str]) -> StackDetection:
    """
    Infer a repository stack from file paths and optional lightweight file snapshots.

    The function is intentionally pure: callers pass the repository file list, and
    may include strings with file content snippets when dependency detection is
    needed, such as "requirements.txt\\nfastapi==0.111.0".
    """
    normalized = [_normalize_entry(file) for file in files]

    has_package_json = _has_file(normalized, "package.json")
    has_node_lockfile = any(
        _has_file(normalized, name)
        for name in ("package-lock.json", "pnpm-lock.yaml", "yarn.lock")
    )
    has_react = (
        _entry_contains(normalized, "package.json", "react")
        or _entry_contains(normalized, "package.json", "@vitejs/plugin-react")
        or _has_file(normalized, "vite.config.js")
        or _has_file(normalized, "vite.config.ts")
        or any(_entry_path(entry).endswith((".jsx", ".tsx")) for entry in normalized)
    )
    has_python = (
        _has_file(normalized, "requirements.txt")
        or _has_file(normalized, "pyproject.toml")
        or _has_file(normalized, "pipfile")
        or _has_file(normalized, "setup.py")
        or any(_entry_path(entry).endswith(".py") for entry in normalized)
    )
    has_fastapi = (
        _entry_contains(normalized, "requirements.txt", "fastapi")
        or _entry_contains(normalized, "pyproject.toml", "fastapi")
        or any("from fastapi import" in entry or "import fastapi" in entry for entry in normalized)
    )
    has_maven = _has_file(normalized, "pom.xml")
    has_docker = any(
        _has_file(normalized, name)
        for name in ("dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")
    )
    has_existing_workflows = any(_entry_path(entry).startswith(".github/workflows/") for entry in normalized)

    if has_package_json or has_node_lockfile:
        language = "javascript"
        framework = "react" if has_react else "node"
        package_manager = _node_package_manager(normalized)
        recommended_workflow: RecommendedWorkflow = "node-ci"
    elif has_python:
        language = "python"
        framework = "fastapi" if has_fastapi else "python"
        package_manager = "pip" if _has_file(normalized, "requirements.txt") else "python"
        recommended_workflow = "python-ci"
    elif has_maven:
        language = "java"
        framework = "maven"
        package_manager = "maven"
        recommended_workflow = "java-ci"
    elif has_docker:
        language = "unknown"
        framework = "docker"
        package_manager = "unknown"
        recommended_workflow = "docker-ci"
    else:
        language = "unknown"
        framework = "unknown"
        package_manager = "unknown"
        recommended_workflow = "generic-ci"

    return {
        "language": language,
        "framework": framework,
        "package_manager": package_manager,
        "has_docker": has_docker,
        "has_existing_workflows": has_existing_workflows,
        "recommended_workflow": recommended_workflow,
    }


def _normalize_entry(file: str) -> str:
    return str(file).strip().replace("\\", "/").lower()


def _has_file(files: list[str], filename: str) -> bool:
    target = filename.strip("/").lower()
    return any(_entry_path(entry).endswith(target) for entry in files)


def _entry_contains(files: list[str], filename: str, needle: str) -> bool:
    target = filename.strip("/").lower()
    value = needle.lower()
    return any(_entry_path(entry).endswith(target) and value in entry for entry in files)


def _entry_path(entry: str) -> str:
    return entry.splitlines()[0].split("::", 1)[0].strip()


def _node_package_manager(files: list[str]) -> str:
    if _has_file(files, "pnpm-lock.yaml"):
        return "pnpm"
    if _has_file(files, "yarn.lock"):
        return "yarn"
    return "npm"
