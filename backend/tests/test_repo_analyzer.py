"""Tests for repository stack detection."""
from __future__ import annotations

from app.services.repo_analyzer import detect_stack


def test_detect_stack_node_react_project():
    result = detect_stack(
        [
            "package.json\n{\"dependencies\":{\"react\":\"^18.3.1\"}}",
            "package-lock.json",
            "vite.config.js",
            "src/App.tsx",
            ".github/workflows/ci.yml",
        ]
    )

    assert result == {
        "language": "javascript",
        "framework": "react",
        "package_manager": "npm",
        "has_docker": False,
        "has_existing_workflows": True,
        "recommended_workflow": "node-ci",
    }


def test_detect_stack_python_fastapi_project():
    result = detect_stack(
        [
            "requirements.txt\nfastapi==0.111.0\nuvicorn[standard]==0.29.0",
            "app/main.py",
        ]
    )

    assert result == {
        "language": "python",
        "framework": "fastapi",
        "package_manager": "pip",
        "has_docker": False,
        "has_existing_workflows": False,
        "recommended_workflow": "python-ci",
    }


def test_detect_stack_fastapi_from_python_source_snapshot():
    result = detect_stack(
        [
            "pyproject.toml\n[project]\ndependencies = []",
            "app/main.py\nfrom fastapi import FastAPI\napp = FastAPI()",
            "compose.yaml",
        ]
    )

    assert result == {
        "language": "python",
        "framework": "fastapi",
        "package_manager": "python",
        "has_docker": True,
        "has_existing_workflows": False,
        "recommended_workflow": "python-ci",
    }


def test_detect_stack_java_maven_project():
    result = detect_stack(["pom.xml", "src/main/java/com/example/App.java"])

    assert result == {
        "language": "java",
        "framework": "maven",
        "package_manager": "maven",
        "has_docker": False,
        "has_existing_workflows": False,
        "recommended_workflow": "java-ci",
    }


def test_detect_stack_docker_project():
    result = detect_stack(["Dockerfile", "deploy/docker-compose.yml"])

    assert result == {
        "language": "unknown",
        "framework": "docker",
        "package_manager": "unknown",
        "has_docker": True,
        "has_existing_workflows": False,
        "recommended_workflow": "docker-ci",
    }


def test_detect_stack_unknown_project():
    result = detect_stack(["README.md", "docs/architecture.md"])

    assert result == {
        "language": "unknown",
        "framework": "unknown",
        "package_manager": "unknown",
        "has_docker": False,
        "has_existing_workflows": False,
        "recommended_workflow": "generic-ci",
    }


def test_detect_stack_node_from_lockfile_and_existing_yaml_workflow():
    result = detect_stack(["pnpm-lock.yaml", "src/index.js", ".github/workflows/build.yaml"])

    assert result == {
        "language": "javascript",
        "framework": "node",
        "package_manager": "pnpm",
        "has_docker": False,
        "has_existing_workflows": True,
        "recommended_workflow": "node-ci",
    }
