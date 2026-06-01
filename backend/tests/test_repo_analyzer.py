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
        "project_dir": ".",
        "detected_projects": [
            {"type": "node", "path": ".", "framework": "react", "package_manager": "npm"},
        ],
        "ci_warnings": [],
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
        "project_dir": ".",
        "detected_projects": [
            {"type": "python", "path": ".", "framework": "fastapi", "package_manager": "pip"},
        ],
        "ci_warnings": [],
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
        "project_dir": ".",
        "detected_projects": [
            {"type": "docker", "path": ".", "framework": "docker", "package_manager": "unknown"},
            {"type": "python", "path": ".", "framework": "fastapi", "package_manager": "python"},
        ],
        "ci_warnings": [],
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
        "project_dir": ".",
        "detected_projects": [
            {"type": "java", "path": ".", "framework": "maven", "package_manager": "maven"},
        ],
        "ci_warnings": [],
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
        "project_dir": ".",
        "detected_projects": [
            {"type": "docker", "path": ".", "framework": "docker", "package_manager": "unknown"},
            {"type": "docker", "path": "deploy", "framework": "docker", "package_manager": "unknown"},
        ],
        "ci_warnings": [],
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
        "project_dir": ".",
        "detected_projects": [],
        "ci_warnings": [],
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
        "project_dir": ".",
        "detected_projects": [
            {"type": "node", "path": ".", "framework": "node", "package_manager": "pnpm"},
        ],
        "ci_warnings": [],
    }


def test_detect_stack_nested_node_project():
    result = detect_stack(["frontend/package.json", "frontend/yarn.lock", "frontend/src/App.tsx"])

    assert result["language"] == "javascript"
    assert result["framework"] == "react"
    assert result["package_manager"] == "yarn"
    assert result["recommended_workflow"] == "node-ci"
    assert result["project_dir"] == "frontend"
    assert result["detected_projects"] == [
        {"type": "node", "path": "frontend", "framework": "react", "package_manager": "yarn"},
    ]
    assert result["ci_warnings"] == []


def test_detect_stack_multi_project_repository():
    result = detect_stack(
        [
            "frontend/package.json",
            "frontend/src/App.jsx",
            "backend/requirements.txt\nfastapi==0.111.0",
            "backend/app/main.py",
        ]
    )

    assert result["language"] == "multi"
    assert result["framework"] == "multi-stack"
    assert result["package_manager"] == "mixed"
    assert result["recommended_workflow"] == "multi-ci"
    assert result["project_dir"] == "backend"
    assert result["detected_projects"] == [
        {"type": "python", "path": "backend", "framework": "fastapi", "package_manager": "pip"},
        {"type": "node", "path": "frontend", "framework": "react", "package_manager": "npm"},
    ]
    assert result["ci_warnings"] == []


def test_detect_stack_warns_about_dependency_review_action():
    result = detect_stack(
        [
            "package.json",
            ".github/workflows/security.yml\n"
            "name: Security\n"
            "on: [pull_request]\n"
            "jobs:\n"
            "  review:\n"
            "    steps:\n"
            "      - uses: actions/dependency-review-action@v5\n",
        ]
    )

    assert result["ci_warnings"]
    assert result["ci_warnings"][0]["path"] == ".github/workflows/security.yml"
    assert "dependency-review-action" in result["ci_warnings"][0]["issue"]
    assert "dependency graph" in result["ci_warnings"][0]["recommendation"]
