"""Tests for generated GitHub Actions CI workflows."""
from __future__ import annotations

import yaml

from app.services.workflow_generator import (
    WORKFLOW_PATH,
    generate_docker_workflow,
    generate_java_workflow,
    generate_node_workflow,
    generate_python_workflow,
    generate_workflow,
)


def _load(workflow: str) -> dict:
    parsed = yaml.safe_load(workflow)
    assert isinstance(parsed, dict)
    assert parsed["on"]
    assert parsed["jobs"]
    return parsed


def test_workflow_path_is_ai_generated_ci():
    assert WORKFLOW_PATH == ".github/workflows/ai-generated-ci.yml"


def test_generate_node_workflow_contains_expected_steps():
    workflow = generate_node_workflow()
    parsed = _load(workflow)

    steps = parsed["jobs"]["node-ci"]["steps"]
    assert {"uses": "actions/checkout@v4", "name": "Checkout repository"} in steps
    assert any(step.get("uses") == "actions/setup-node@v4" and step["with"]["node-version"] == 20 for step in steps)
    install_step = next(step for step in steps if step["name"] == "Install dependencies")
    test_step = next(step for step in steps if step["name"] == "Run tests")
    build_step = next(step for step in steps if step["name"] == "Build")
    assert "if [ -f package-lock.json ]; then" in install_step["run"]
    assert "npm ci" in install_step["run"]
    assert "npm install" in install_step["run"]
    assert "npm test" in test_step["run"]
    assert "No test script found." in test_step["run"]
    assert "npm run build" in build_step["run"]
    assert "No build script found." in build_step["run"]


def test_generate_node_workflow_supports_pnpm():
    workflow = generate_node_workflow(package_manager="pnpm")
    parsed = _load(workflow)

    steps = parsed["jobs"]["node-ci"]["steps"]
    install_step = next(step for step in steps if step["name"] == "Install dependencies")
    assert install_step["run"].strip() == "pnpm install --frozen-lockfile"
    assert "pnpm test" in next(step for step in steps if step["name"] == "Run tests")["run"]


def test_generate_python_workflow_contains_expected_steps():
    workflow = generate_python_workflow()
    parsed = _load(workflow)

    steps = parsed["jobs"]["python-ci"]["steps"]
    assert {"uses": "actions/checkout@v4", "name": "Checkout repository"} in steps
    assert any(
        step.get("uses") == "actions/setup-python@v5"
        and step["with"]["python-version"] == "3.11"
        for step in steps
    )
    install_step = next(step for step in steps if step["name"] == "Install dependencies")
    test_step = next(step for step in steps if step["name"] == "Run tests")
    assert "if [ -f requirements.txt ]; then pip install -r requirements.txt; fi" in install_step["run"]
    assert "pip install pytest" in install_step["run"]
    assert 'if [ -d tests ]; then pytest; else echo "No tests folder found."; fi' in test_step["run"]


def test_generate_java_workflow_contains_expected_steps():
    workflow = generate_java_workflow()
    parsed = _load(workflow)

    steps = parsed["jobs"]["java-ci"]["steps"]
    assert {"uses": "actions/checkout@v4", "name": "Checkout repository"} in steps
    assert any(
        step.get("uses") == "actions/setup-java@v4"
        and step["with"]["distribution"] == "temurin"
        and step["with"]["java-version"] == 17
        for step in steps
    )
    assert any(step.get("run") == "mvn test" for step in steps)


def test_generate_docker_workflow_contains_expected_steps():
    workflow = generate_docker_workflow()
    parsed = _load(workflow)

    steps = parsed["jobs"]["docker-ci"]["steps"]
    assert {"uses": "actions/checkout@v4", "name": "Checkout repository"} in steps
    assert any(step.get("run") == "docker build -t ai-generated-app ." for step in steps)


def test_generate_workflow_routes_by_recommendation():
    assert generate_workflow({"recommended_workflow": "node-ci"}) == generate_node_workflow()
    assert generate_workflow(
        {"recommended_workflow": "node-ci", "package_manager": "yarn"}
    ) == generate_node_workflow("yarn")
    assert generate_workflow({"recommended_workflow": "python-ci"}) == generate_python_workflow()
    assert generate_workflow({"recommended_workflow": "java-ci"}) == generate_java_workflow()
    assert generate_workflow({"recommended_workflow": "docker-ci"}) == generate_docker_workflow()

    generic = generate_workflow({"recommended_workflow": "generic-ci"})
    assert "generic-ci:" in generic
    assert "No specific stack detected." in generic
