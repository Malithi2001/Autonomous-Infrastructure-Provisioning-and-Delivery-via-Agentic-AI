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
    assert "if [ ! -f package.json ]; then" in install_step["run"]
    assert "if [ -f pnpm-lock.yaml ]; then" in install_step["run"]
    assert "npm ci" in install_step["run"]
    assert "npm install" in install_step["run"]
    assert "npm test" in test_step["run"]
    assert "pnpm test" in test_step["run"]
    assert "yarn test" in test_step["run"]
    assert "No test script found." in test_step["run"]
    assert "npm run build" in build_step["run"]
    assert "No build script found." in build_step["run"]


def test_generate_node_workflow_supports_pnpm():
    workflow = generate_node_workflow(package_manager="pnpm")
    parsed = _load(workflow)

    steps = parsed["jobs"]["node-ci"]["steps"]
    install_step = next(step for step in steps if step["name"] == "Install dependencies")
    assert "pnpm install --frozen-lockfile" in install_step["run"]
    assert 'elif [ "pnpm" = "pnpm" ]; then' in install_step["run"]
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
    assert "if [ -f requirements.txt ]; then" in install_step["run"]
    assert "python -m pip install -r requirements.txt" in install_step["run"]
    assert "pyproject.toml does not define an installable package" in install_step["run"]
    assert "python -m pip install pytest" in install_step["run"]
    assert "pytest || status=$?" in test_step["run"]
    assert "pipenv run pytest || status=$?" in test_step["run"]
    assert 'if [ "${status:-0}" -eq 5 ]; then' in test_step["run"]
    assert "No pytest tests collected." in test_step["run"]
    assert "No Python tests found." in test_step["run"]


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
    run_step = next(step for step in steps if step["name"] == "Run Java tests")
    assert "mvn -B test" in run_step["run"]
    assert "./gradlew test" in run_step["run"]


def test_generate_docker_workflow_contains_expected_steps():
    workflow = generate_docker_workflow()
    parsed = _load(workflow)

    steps = parsed["jobs"]["docker-ci"]["steps"]
    assert {"uses": "actions/checkout@v4", "name": "Checkout repository"} in steps
    run_step = next(step for step in steps if step["name"] == "Validate Docker configuration")
    assert "docker build -t ai-generated-app ." in run_step["run"]
    assert "docker compose config" in run_step["run"]


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


def test_generate_node_workflow_uses_nested_project_directory():
    workflow = generate_node_workflow(project_dir="frontend")
    parsed = _load(workflow)

    defaults = parsed["jobs"]["node-ci"]["defaults"]["run"]
    assert defaults["working-directory"] == "frontend"


def test_generate_multi_workflow_contains_jobs_for_detected_projects():
    workflow = generate_workflow(
        {
            "recommended_workflow": "multi-ci",
            "detected_projects": [
                {"type": "python", "path": "backend", "framework": "fastapi", "package_manager": "pip"},
                {"type": "node", "path": "frontend", "framework": "react", "package_manager": "npm"},
            ],
        }
    )
    parsed = _load(workflow)

    assert "python-ci-backend" in parsed["jobs"]
    assert "node-ci-frontend" in parsed["jobs"]
    assert parsed["jobs"]["python-ci-backend"]["defaults"]["run"]["working-directory"] == "backend"
    assert parsed["jobs"]["node-ci-frontend"]["defaults"]["run"]["working-directory"] == "frontend"
