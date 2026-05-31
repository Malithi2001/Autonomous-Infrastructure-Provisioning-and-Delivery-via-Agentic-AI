"""Rule-based fix recommendations for classified CI/CD failures."""
from __future__ import annotations

import re
from typing import Any

RiskLevel = str


def get_fix_recommendation(
    label: str,
    log_text: str,
    repo_files: list[str] | None = None,
) -> dict[str, Any]:
    """
    Return a demo-friendly remediation recommendation for a predicted failure.

    The engine intentionally returns recommendations only. It does not generate
    patches or modify repository files.
    """
    normalized_label = (label or "unknown_failure").strip() or "unknown_failure"
    cleaned_log = (log_text or "").strip()
    files = repo_files or []
    context = _context(cleaned_log, files)

    builders = {
        "npm_missing_test_script": _npm_missing_test_script,
        "npm_missing_lockfile": _npm_missing_lockfile,
        "pytest_not_found": _pytest_not_found,
        "python_missing_dependency": _python_missing_dependency,
        "wrong_runtime_version": _wrong_runtime_version,
        "docker_build_failed": _docker_build_failed,
    }
    builder = builders.get(normalized_label, _generic_recommendation)
    return builder(normalized_label, context)


def _context(log_text: str, repo_files: list[str]) -> dict[str, Any]:
    paths = [str(path).strip().replace("\\", "/") for path in repo_files if str(path).strip()]
    return {
        "has_package_json": any(path.endswith("package.json") for path in paths),
        "has_package_lock": any(path.endswith("package-lock.json") for path in paths),
        "has_requirements": any(path.endswith("requirements.txt") for path in paths),
        "has_pyproject": any(path.endswith("pyproject.toml") for path in paths),
        "has_dockerfile": any(path.lower().endswith("dockerfile") for path in paths),
        "missing_python_module": _extract_missing_python_module(log_text),
    }


def _recommendation(
    *,
    summary: str,
    root_cause: str,
    safe_fix_available: bool,
    recommended_changes: list[str],
    risk_level: RiskLevel,
    requires_approval: bool,
) -> dict[str, Any]:
    return {
        "summary": summary,
        "root_cause": root_cause,
        "safe_fix_available": safe_fix_available,
        "recommended_changes": recommended_changes,
        "risk_level": risk_level,
        "requires_approval": requires_approval,
    }


def _npm_missing_test_script(label: str, context: dict[str, Any]) -> dict[str, Any]:
    changes = [
        "Review package.json and confirm whether the project has a real test command.",
        "If tests exist, add a scripts.test entry such as npm test, vitest, jest, or the project-specific runner.",
        "If no tests exist yet, update the workflow to skip npm test or run npm run build until tests are added.",
    ]
    if not context["has_package_json"]:
        changes.insert(0, "Confirm package.json is present in the repository root or correct working directory.")
    return _recommendation(
        summary="The CI job ran npm test, but package.json does not define a test script.",
        root_cause=(
            "The Node.js workflow expects scripts.test to exist. "
            "npm exits with Missing script: test before tests run."
        ),
        safe_fix_available=True,
        recommended_changes=changes,
        risk_level="low",
        requires_approval=False,
    )


def _npm_missing_lockfile(label: str, context: dict[str, Any]) -> dict[str, Any]:
    changes = [
        "Run npm install locally to generate package-lock.json.",
        "Commit package-lock.json so npm ci can perform reproducible installs in CI.",
        (
            "If the project intentionally does not use npm lockfiles, "
            "change the workflow install step from npm ci to npm install."
        ),
    ]
    if context["has_package_lock"]:
        changes.append(
            "Check the workflow working-directory because package-lock.json appears to exist in the file list."
        )
    return _recommendation(
        summary="The CI job used npm ci but no npm lockfile was available.",
        root_cause="npm ci requires package-lock.json or npm-shrinkwrap.json to already exist and match package.json.",
        safe_fix_available=True,
        recommended_changes=changes,
        risk_level="low",
        requires_approval=False,
    )


def _pytest_not_found(label: str, context: dict[str, Any]) -> dict[str, Any]:
    dependency_file = "requirements.txt" if context["has_requirements"] else "pyproject.toml"
    return _recommendation(
        summary="The test command tried to run pytest, but pytest is not installed in the CI environment.",
        root_cause="The workflow installs dependencies that do not include pytest before running the test command.",
        safe_fix_available=True,
        recommended_changes=[
            f"Add pytest to {dependency_file} or the project's development/test dependency group.",
            "Ensure the workflow installs test dependencies before running pytest.",
            "Prefer python -m pytest in CI so the command uses the selected Python environment.",
        ],
        risk_level="low",
        requires_approval=False,
    )


def _python_missing_dependency(label: str, context: dict[str, Any]) -> dict[str, Any]:
    module_name = context.get("missing_python_module")
    dependency_hint = f" for '{module_name}'" if module_name else ""
    return _recommendation(
        summary=f"A Python dependency{dependency_hint} is missing during CI import or test execution.",
        root_cause="The CI environment does not install all packages required by the application or tests.",
        safe_fix_available=True,
        recommended_changes=[
            "Add the missing package to requirements.txt, pyproject.toml, or the appropriate dependency group.",
            (
                "Verify the workflow installs dependencies before running imports, "
                "tests, or the application startup command."
            ),
            "Run the backend tests locally in a clean virtual environment to confirm the dependency list is complete.",
        ],
        risk_level="low",
        requires_approval=False,
    )


def _wrong_runtime_version(label: str, context: dict[str, Any]) -> dict[str, Any]:
    return _recommendation(
        summary="The workflow is using a runtime version that does not match the project requirements.",
        root_cause="CI selected an incompatible Node.js, Python, Java, npm, pnpm, or Docker base runtime.",
        safe_fix_available=True,
        recommended_changes=[
            (
                "Check package.json engines, .nvmrc, pyproject.toml, runtime.txt, "
                "pom.xml, or Dockerfile for required versions."
            ),
            "Update the workflow setup action to use the required runtime version.",
            "Rerun CI after the version change because runtime changes can alter dependency resolution.",
        ],
        risk_level="medium",
        requires_approval=True,
    )


def _docker_build_failed(label: str, context: dict[str, Any]) -> dict[str, Any]:
    changes = [
        "Rebuild the Docker image locally with the same Dockerfile and build context used in CI.",
        "Check COPY paths, .dockerignore, missing build artifacts, and package install commands.",
        "Keep the workflow change limited to docker build validation until the Dockerfile fix is reviewed.",
    ]
    if not context["has_dockerfile"]:
        changes.insert(0, "Confirm the repository contains a Dockerfile at the path used by the workflow.")
    return _recommendation(
        summary="The container image failed during docker build.",
        root_cause="A Dockerfile instruction, missing file, build context issue, or dependency install command failed.",
        safe_fix_available=True,
        recommended_changes=changes,
        risk_level="medium",
        requires_approval=True,
    )


def _generic_recommendation(label: str, context: dict[str, Any]) -> dict[str, Any]:
    return _recommendation(
        summary=f"No safe automated recommendation is available for {label}.",
        root_cause="The classifier label is not mapped to a low-risk remediation pattern yet.",
        safe_fix_available=False,
        recommended_changes=[
            "Review the full CI/CD logs manually.",
            "Add a labeled example to the training dataset if this failure pattern repeats.",
            "Create a project-specific remediation rule only after the fix is understood.",
        ],
        risk_level="medium",
        requires_approval=False,
    )


def _extract_missing_python_module(log_text: str) -> str | None:
    patterns = [
        r"ModuleNotFoundError:\s*No module named ['\"]([^'\"]+)['\"]",
        r"No module named ['\"]([^'\"]+)['\"]",
        r"ImportError:\s*No module named\s+([A-Za-z0-9_.-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, log_text)
        if match:
            return match.group(1)
    return None
