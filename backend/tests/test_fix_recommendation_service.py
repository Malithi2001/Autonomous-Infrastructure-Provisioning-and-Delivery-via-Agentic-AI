"""Tests for rule-based CI/CD fix recommendations."""
from __future__ import annotations

from app.services.fix_recommendation_service import get_fix_recommendation


def test_npm_missing_test_script_recommendation_is_safe_and_demo_friendly():
    result = get_fix_recommendation(
        "npm_missing_test_script",
        "npm ERR! Missing script: test",
        ["package.json", "src/App.jsx"],
    )

    assert result["summary"] == "The CI job ran npm test, but package.json does not define a test script."
    assert result["safe_fix_available"] is True
    assert result["risk_level"] == "low"
    assert result["requires_approval"] is False
    assert any("scripts.test" in change for change in result["recommended_changes"])


def test_npm_missing_lockfile_recommendation_mentions_package_lock():
    result = get_fix_recommendation("npm_missing_lockfile", "npm ci requires package-lock.json")

    assert result["safe_fix_available"] is True
    assert result["risk_level"] == "low"
    assert any("package-lock.json" in change for change in result["recommended_changes"])


def test_pytest_not_found_recommendation_mentions_test_dependency():
    result = get_fix_recommendation("pytest_not_found", "pytest: command not found", ["requirements.txt"])

    assert result["safe_fix_available"] is True
    assert result["risk_level"] == "low"
    assert result["recommended_changes"][0].startswith("Add pytest to requirements.txt")


def test_python_missing_dependency_extracts_module_name():
    result = get_fix_recommendation(
        "python_missing_dependency",
        "ModuleNotFoundError: No module named 'fastapi'",
    )

    assert "fastapi" in result["summary"]
    assert result["safe_fix_available"] is True


def test_wrong_runtime_version_requires_approval_for_future_change():
    result = get_fix_recommendation("wrong_runtime_version", "Node.js 12 but package requires >=18")

    assert result["safe_fix_available"] is True
    assert result["risk_level"] == "medium"
    assert result["requires_approval"] is True


def test_docker_build_failed_requires_approval_for_future_change():
    result = get_fix_recommendation("docker_build_failed", "docker build failed", ["Dockerfile"])

    assert result["safe_fix_available"] is True
    assert result["risk_level"] == "medium"
    assert result["requires_approval"] is True


def test_unknown_label_returns_no_safe_fix():
    result = get_fix_recommendation("new_failure", "unmapped log")

    assert result["safe_fix_available"] is False
    assert result["risk_level"] == "medium"
    assert result["requires_approval"] is False
