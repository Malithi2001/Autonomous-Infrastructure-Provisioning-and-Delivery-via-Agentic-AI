"""Pure repository stack detection for CI/CD workflow recommendations."""
from __future__ import annotations

from typing import Literal, TypedDict


RecommendedWorkflow = Literal["node-ci", "python-ci", "java-ci", "docker-ci", "multi-ci", "generic-ci"]


class DetectedProject(TypedDict):
    type: str
    path: str
    framework: str
    package_manager: str


class CIWarning(TypedDict):
    severity: str
    path: str
    issue: str
    recommendation: str


class StackDetection(TypedDict):
    language: str
    framework: str
    package_manager: str
    has_docker: bool
    has_existing_workflows: bool
    recommended_workflow: RecommendedWorkflow
    project_dir: str
    detected_projects: list[DetectedProject]
    ci_warnings: list[CIWarning]


class _Entry(TypedDict):
    path: str
    lower_path: str
    content: str
    lower_content: str


def detect_stack(files: list[str]) -> StackDetection:
    """
    Infer repository stack, primary project directory, and CI recommendation.

    The function is intentionally pure: callers pass repository file paths, and
    may include lightweight file snapshots when dependency detection is useful,
    such as ``"requirements.txt\\nfastapi==0.111.0"``.
    """
    entries = [_entry(file) for file in files if str(file).strip()]

    node_projects = _node_projects(entries)
    python_projects = _python_projects(entries)
    java_projects = _java_projects(entries)
    docker_projects = _docker_projects(entries)
    app_projects = [*node_projects, *python_projects, *java_projects]
    detected_projects = _sort_projects([*app_projects, *docker_projects])

    has_docker = bool(docker_projects)
    has_existing_workflows = any(entry["lower_path"].startswith(".github/workflows/") for entry in entries)
    ci_warnings = _ci_warnings(entries)

    app_project_kinds = {project["type"] for project in app_projects}
    if len(app_project_kinds) > 1 or len(app_projects) > 1:
        primary = _primary_project(app_projects)
        return {
            "language": "multi",
            "framework": "multi-stack",
            "package_manager": "mixed",
            "has_docker": has_docker,
            "has_existing_workflows": has_existing_workflows,
            "recommended_workflow": "multi-ci",
            "project_dir": primary["path"] if primary else ".",
            "detected_projects": detected_projects,
            "ci_warnings": ci_warnings,
        }

    if node_projects:
        project = node_projects[0]
        return {
            "language": "javascript",
            "framework": project["framework"],
            "package_manager": project["package_manager"],
            "has_docker": has_docker,
            "has_existing_workflows": has_existing_workflows,
            "recommended_workflow": "node-ci",
            "project_dir": project["path"],
            "detected_projects": detected_projects,
            "ci_warnings": ci_warnings,
        }

    if python_projects:
        project = python_projects[0]
        return {
            "language": "python",
            "framework": project["framework"],
            "package_manager": project["package_manager"],
            "has_docker": has_docker,
            "has_existing_workflows": has_existing_workflows,
            "recommended_workflow": "python-ci",
            "project_dir": project["path"],
            "detected_projects": detected_projects,
            "ci_warnings": ci_warnings,
        }

    if java_projects:
        project = java_projects[0]
        return {
            "language": "java",
            "framework": project["framework"],
            "package_manager": project["package_manager"],
            "has_docker": has_docker,
            "has_existing_workflows": has_existing_workflows,
            "recommended_workflow": "java-ci",
            "project_dir": project["path"],
            "detected_projects": detected_projects,
            "ci_warnings": ci_warnings,
        }

    if docker_projects:
        project = docker_projects[0]
        return {
            "language": "unknown",
            "framework": "docker",
            "package_manager": "unknown",
            "has_docker": True,
            "has_existing_workflows": has_existing_workflows,
            "recommended_workflow": "docker-ci",
            "project_dir": project["path"],
            "detected_projects": detected_projects,
            "ci_warnings": ci_warnings,
        }

    return {
        "language": "unknown",
        "framework": "unknown",
        "package_manager": "unknown",
        "has_docker": False,
        "has_existing_workflows": has_existing_workflows,
        "recommended_workflow": "generic-ci",
        "project_dir": ".",
        "detected_projects": [],
        "ci_warnings": ci_warnings,
    }


def _entry(file: str) -> _Entry:
    value = str(file).strip().replace("\\", "/")
    path = value.splitlines()[0].split("::", 1)[0].strip()
    while path.startswith("./"):
        path = path[2:]
    path = path.strip("/") or "."
    return {
        "path": path,
        "lower_path": path.lower(),
        "content": value,
        "lower_content": value.lower(),
    }


def _node_projects(entries: list[_Entry]) -> list[DetectedProject]:
    node_manifest_names = {
        "package.json",
        "package-lock.json",
        "npm-shrinkwrap.json",
        "pnpm-lock.yaml",
        "yarn.lock",
    }
    project_dirs = {
        _dir_name(entry["path"])
        for entry in entries
        if _basename(entry["lower_path"]) in node_manifest_names
    }
    projects: list[DetectedProject] = [
        {
            "type": "node",
            "path": project_dir,
            "framework": "react" if _has_react(entries, project_dir) else "node",
            "package_manager": _node_package_manager(entries, project_dir),
        }
        for project_dir in project_dirs
    ]
    return _sort_projects(projects)


def _python_projects(entries: list[_Entry]) -> list[DetectedProject]:
    manifest_names = {"requirements.txt", "pyproject.toml", "pipfile", "setup.py", "setup.cfg"}
    project_dirs = {
        _dir_name(entry["path"])
        for entry in entries
        if _basename(entry["lower_path"]) in manifest_names
    }
    if not project_dirs and any(entry["lower_path"].endswith(".py") for entry in entries):
        project_dirs = {"."}

    projects: list[DetectedProject] = [
        {
            "type": "python",
            "path": project_dir,
            "framework": "fastapi" if _has_fastapi(entries, project_dir) else "python",
            "package_manager": _python_package_manager(entries, project_dir),
        }
        for project_dir in project_dirs
    ]
    return _sort_projects(projects)


def _java_projects(entries: list[_Entry]) -> list[DetectedProject]:
    manifest_names = {"pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"}
    project_dirs = {
        _dir_name(entry["path"])
        for entry in entries
        if _basename(entry["lower_path"]) in manifest_names
    }
    projects: list[DetectedProject] = []
    for project_dir in project_dirs:
        has_maven = _has_file_in_dir(entries, project_dir, {"pom.xml"})
        projects.append(
            {
                "type": "java",
                "path": project_dir,
                "framework": "maven" if has_maven else "gradle",
                "package_manager": "maven" if has_maven else "gradle",
            }
        )
    return _sort_projects(projects)


def _docker_projects(entries: list[_Entry]) -> list[DetectedProject]:
    docker_names = {"dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}
    project_dirs = {
        _dir_name(entry["path"])
        for entry in entries
        if _basename(entry["lower_path"]) in docker_names
    }
    projects: list[DetectedProject] = [
        {
            "type": "docker",
            "path": project_dir,
            "framework": "docker",
            "package_manager": "unknown",
        }
        for project_dir in project_dirs
    ]
    return _sort_projects(projects)


def _has_react(entries: list[_Entry], project_dir: str) -> bool:
    return (
        _entry_contains(entries, project_dir, "package.json", "react")
        or _entry_contains(entries, project_dir, "package.json", "@vitejs/plugin-react")
        or _has_file_in_dir(entries, project_dir, {"vite.config.js", "vite.config.ts"})
        or any(
            _is_inside(entry["path"], project_dir) and entry["lower_path"].endswith((".jsx", ".tsx"))
            for entry in entries
        )
    )


def _has_fastapi(entries: list[_Entry], project_dir: str) -> bool:
    return (
        _entry_contains(entries, project_dir, "requirements.txt", "fastapi")
        or _entry_contains(entries, project_dir, "pyproject.toml", "fastapi")
        or any(
            _is_inside(entry["path"], project_dir)
            and ("from fastapi import" in entry["lower_content"] or "import fastapi" in entry["lower_content"])
            for entry in entries
        )
    )


def _ci_warnings(entries: list[_Entry]) -> list[CIWarning]:
    warnings: list[CIWarning] = []
    for entry in entries:
        path = entry["lower_path"]
        if not path.startswith(".github/workflows/") or not path.endswith((".yml", ".yaml")):
            continue

        content = entry["lower_content"]
        if "actions/dependency-review-action" in content:
            warnings.append(
                {
                    "severity": "warning",
                    "path": entry["path"],
                    "issue": (
                        "Existing workflow uses actions/dependency-review-action, "
                        "which can fail when dependency graph is disabled or unsupported."
                    ),
                    "recommendation": (
                        "Enable dependency graph in repository security settings, "
                        "or make the dependency-review step optional/non-blocking. "
                        "The generated AI workflow does not require dependency review."
                    ),
                }
            )

        if "aws-actions/configure-aws-credentials" in content and "aws-region:" not in content:
            warnings.append(
                {
                    "severity": "error",
                    "path": entry["path"],
                    "issue": (
                        "Existing workflow uses aws-actions/configure-aws-credentials "
                        "without the required aws-region input."
                    ),
                    "recommendation": (
                        "Add `aws-region: ${{ secrets.AWS_REGION }}` or a literal region such as "
                        "`us-east-1` to the configure-aws-credentials step. If this is only a CI "
                        "workflow, remove the AWS credentials step because the generated AI workflow "
                        "does not require AWS deployment credentials."
                    ),
                }
            )

        if "pull_request_target:" in content:
            warnings.append(
                {
                    "severity": "warning",
                    "path": entry["path"],
                    "issue": "Existing workflow uses pull_request_target, which has elevated token permissions.",
                    "recommendation": (
                        "Review the workflow carefully before allowing automated changes to run on pull requests."
                    ),
                }
            )

    return warnings


def _node_package_manager(entries: list[_Entry], project_dir: str) -> str:
    if _has_file_in_dir(entries, project_dir, {"pnpm-lock.yaml"}):
        return "pnpm"
    if _has_file_in_dir(entries, project_dir, {"yarn.lock"}):
        return "yarn"
    return "npm"


def _python_package_manager(entries: list[_Entry], project_dir: str) -> str:
    if _has_file_in_dir(entries, project_dir, {"requirements.txt"}):
        return "pip"
    if _has_file_in_dir(entries, project_dir, {"pipfile"}):
        return "pipenv"
    if _has_file_in_dir(entries, project_dir, {"poetry.lock"}):
        return "poetry"
    return "python"


def _entry_contains(entries: list[_Entry], project_dir: str, filename: str, needle: str) -> bool:
    target = filename.lower()
    value = needle.lower()
    return any(
        _is_inside(entry["path"], project_dir)
        and _basename(entry["lower_path"]) == target
        and value in entry["lower_content"]
        for entry in entries
    )


def _has_file_in_dir(entries: list[_Entry], project_dir: str, filenames: set[str]) -> bool:
    normalized = {filename.lower() for filename in filenames}
    return any(
        _dir_name(entry["path"]) == project_dir and _basename(entry["lower_path"]) in normalized
        for entry in entries
    )


def _dir_name(path: str) -> str:
    normalized = path.strip("/")
    if not normalized or "/" not in normalized:
        return "."
    return normalized.rsplit("/", 1)[0]


def _basename(path: str) -> str:
    return path.strip("/").rsplit("/", 1)[-1]


def _is_inside(path: str, project_dir: str) -> bool:
    if project_dir == ".":
        return True
    normalized_dir = project_dir.rstrip("/")
    return path == normalized_dir or path.startswith(f"{normalized_dir}/")


def _sort_projects(projects: list[DetectedProject]) -> list[DetectedProject]:
    seen: set[tuple[str, str]] = set()
    unique: list[DetectedProject] = []
    for project in projects:
        key = (project["type"], project["path"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(project)
    return sorted(unique, key=lambda project: (0 if project["path"] == "." else 1, project["path"], project["type"]))


def _primary_project(projects: list[DetectedProject]) -> DetectedProject | None:
    ordered = _sort_projects(projects)
    return ordered[0] if ordered else None
