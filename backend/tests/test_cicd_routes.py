"""Tests for CI/CD repository analysis and workflow generation endpoints."""
from __future__ import annotations

import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import cicd


def _build_cicd_app() -> FastAPI:
    test_app = FastAPI(title="CI/CD Route Test App")
    test_app.include_router(cicd.router, prefix="/api/v1/cicd")
    return test_app


app = _build_cicd_app()


def test_analyze_files_recommends_node_react_workflow_without_auth():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/cicd/analyze-files",
            json={"files": ["package.json", "src/App.jsx", "vite.config.js", "Dockerfile"]},
        )

    assert response.status_code == 200
    assert response.json() == {
        "language": "javascript",
        "framework": "react",
        "package_manager": "npm",
        "has_docker": True,
        "has_existing_workflows": False,
        "recommended_workflow": "node-ci",
    }


def test_generate_workflow_returns_stack_path_and_valid_yaml_without_auth():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/cicd/generate-workflow",
            json={"files": ["requirements.txt\nfastapi==0.111.0", "tests/test_app.py"]},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["stack"]["language"] == "python"
    assert body["stack"]["framework"] == "fastapi"
    assert body["stack"]["recommended_workflow"] == "python-ci"
    assert body["path"] == ".github/workflows/ai-generated-ci.yml"
    assert "actions/setup-python@v5" in body["workflow_yaml"]
    assert "python-version: '3.11'" in body["workflow_yaml"]

    parsed = yaml.safe_load(body["workflow_yaml"])
    assert parsed["jobs"]["python-ci"]["runs-on"] == "ubuntu-latest"


def test_generate_workflow_returns_node_workflow_without_github_calls():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/cicd/generate-workflow",
            json={"files": ["package.json", "src/App.jsx"]},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["stack"]["recommended_workflow"] == "node-ci"
    assert body["path"] == ".github/workflows/ai-generated-ci.yml"
    assert "actions/setup-node@v4" in body["workflow_yaml"]

    parsed = yaml.safe_load(body["workflow_yaml"])
    assert parsed["jobs"]["node-ci"]["steps"][1]["uses"] == "actions/setup-node@v4"


def test_generate_workflow_returns_java_workflow_without_github_calls():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/cicd/generate-workflow",
            json={"files": ["pom.xml", "src/main/java/com/example/App.java"]},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["stack"]["recommended_workflow"] == "java-ci"
    assert "actions/setup-java@v4" in body["workflow_yaml"]

    parsed = yaml.safe_load(body["workflow_yaml"])
    assert parsed["jobs"]["java-ci"]["steps"][1]["uses"] == "actions/setup-java@v4"


def test_generate_workflow_returns_docker_workflow_without_github_calls():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/cicd/generate-workflow",
            json={"files": ["Dockerfile"]},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["stack"]["recommended_workflow"] == "docker-ci"
    assert "docker build -t ai-generated-app ." in body["workflow_yaml"]

    parsed = yaml.safe_load(body["workflow_yaml"])
    assert parsed["jobs"]["docker-ci"]["steps"][1]["run"] == "docker build -t ai-generated-app ."
