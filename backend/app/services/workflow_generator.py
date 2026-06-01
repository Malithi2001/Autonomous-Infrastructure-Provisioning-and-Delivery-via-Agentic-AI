"""Generate conservative GitHub Actions CI workflows from repository stack detection."""
from __future__ import annotations

import re
from collections.abc import Mapping
from textwrap import dedent
from typing import Any


WORKFLOW_PATH = ".github/workflows/ai-generated-ci.yml"
_SUPPORTED_PROJECT_TYPES = {"node", "python", "java"}


def generate_workflow(stack: Mapping[str, Any]) -> str:
    """Return a GitHub Actions workflow YAML string for a detected repository stack."""
    recommended = stack.get("recommended_workflow")
    project_dir = _project_dir(stack)

    if recommended == "multi-ci":
        return generate_multi_workflow(stack)
    if recommended == "node-ci":
        return generate_node_workflow(
            package_manager=str(stack.get("package_manager") or "npm"),
            project_dir=project_dir,
        )
    if recommended == "python-ci":
        return generate_python_workflow(project_dir=project_dir)
    if recommended == "java-ci":
        return generate_java_workflow(project_dir=project_dir)
    if recommended == "docker-ci":
        return generate_docker_workflow(project_dir=project_dir)
    return generate_generic_workflow()


def generate_node_workflow(package_manager: str = "npm", *, project_dir: str = ".") -> str:
    return _workflow("AI Generated Node CI", [_node_job("node-ci", project_dir, package_manager)])


def generate_python_workflow(*, project_dir: str = ".") -> str:
    return _workflow("AI Generated Python CI", [_python_job("python-ci", project_dir)])


def generate_java_workflow(*, project_dir: str = ".") -> str:
    return _workflow("AI Generated Java CI", [_java_job("java-ci", project_dir)])


def generate_docker_workflow(*, project_dir: str = ".") -> str:
    return _workflow("AI Generated Docker CI", [_docker_job("docker-ci", project_dir)])


def generate_generic_workflow() -> str:
    return _workflow(
        "AI Generated CI",
        [
            f"""
  generic-ci:
    name: Repository inspection
    runs-on: ubuntu-latest
    timeout-minutes: 10
    defaults:
      run:
        shell: bash
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Inspect repository
        run: |
{_indent_shell('''
          echo "No specific stack detected."
          find . -maxdepth 3 -type f | sort | sed -n '1,200p'
''')}
            """
        ],
    )


def generate_multi_workflow(stack: Mapping[str, Any]) -> str:
    projects = _detected_projects(stack)
    jobs: list[str] = []

    for project in projects:
        project_type = str(project.get("type") or "")
        if project_type not in _SUPPORTED_PROJECT_TYPES:
            continue

        project_dir = _project_dir(project)
        job_id = _job_id(f"{project_type}-ci", project_dir)
        if project_type == "node":
            jobs.append(_node_job(job_id, project_dir, str(project.get("package_manager") or "npm")))
        elif project_type == "python":
            jobs.append(_python_job(job_id, project_dir))
        elif project_type == "java":
            jobs.append(_java_job(job_id, project_dir))

    if not jobs:
        return generate_generic_workflow()
    return _workflow("AI Generated Multi-Stack CI", jobs)


def _workflow(name: str, jobs: list[str]) -> str:
    workflow = f"""
name: {name}

'on':
  push:
    branches: [main, master]
  pull_request:

permissions:
  contents: read

jobs:
{''.join(jobs)}
    """
    return _validated(workflow)


def _node_job(job_id: str, project_dir: str, package_manager: str) -> str:
    package_manager = package_manager if package_manager in {"npm", "pnpm", "yarn"} else "npm"
    display_dir = _display_dir(project_dir)
    return f"""
  {job_id}:
    name: Node CI ({display_dir})
    runs-on: ubuntu-latest
    timeout-minutes: 20
    env:
      CI: true
    defaults:
      run:
        shell: bash
{_working_directory_line(project_dir)}
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 20

      - name: Enable package manager shims
        run: corepack enable || true

      - name: Install dependencies
        run: |
{_indent_shell(_node_install_command(package_manager))}

      - name: Run tests
        run: |
{_indent_shell(_node_script_command("test"))}

      - name: Build
        run: |
{_indent_shell(_node_script_command("build"))}
"""


def _python_job(job_id: str, project_dir: str) -> str:
    display_dir = _display_dir(project_dir)
    return f"""
  {job_id}:
    name: Python CI ({display_dir})
    runs-on: ubuntu-latest
    timeout-minutes: 20
    defaults:
      run:
        shell: bash
{_working_directory_line(project_dir)}
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
{_indent_shell(_python_install_command())}

      - name: Run tests
        run: |
{_indent_shell(_python_test_command())}
"""


def _java_job(job_id: str, project_dir: str) -> str:
    display_dir = _display_dir(project_dir)
    return f"""
  {job_id}:
    name: Java CI ({display_dir})
    runs-on: ubuntu-latest
    timeout-minutes: 25
    defaults:
      run:
        shell: bash
{_working_directory_line(project_dir)}
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Java
        uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: 17

      - name: Run Java tests
        run: |
{_indent_shell(_java_test_command())}
"""


def _docker_job(job_id: str, project_dir: str) -> str:
    display_dir = _display_dir(project_dir)
    return f"""
  {job_id}:
    name: Docker validation ({display_dir})
    runs-on: ubuntu-latest
    timeout-minutes: 25
    defaults:
      run:
        shell: bash
{_working_directory_line(project_dir)}
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Validate Docker configuration
        run: |
{_indent_shell(_docker_validate_command())}
"""


def _node_install_command(package_manager: str) -> str:
    preferred = package_manager if package_manager in {"npm", "pnpm", "yarn"} else "npm"
    return f"""
    if [ ! -f package.json ]; then
      echo "No package.json found in this project directory."
      exit 0
    fi

    if [ -f pnpm-lock.yaml ]; then
      pnpm install --frozen-lockfile
    elif [ -f yarn.lock ]; then
      yarn install --frozen-lockfile
    elif [ -f package-lock.json ] || [ -f npm-shrinkwrap.json ]; then
      npm ci
    elif [ "{preferred}" = "pnpm" ]; then
      pnpm install
    elif [ "{preferred}" = "yarn" ]; then
      yarn install
    else
      npm install
    fi
    """


def _node_script_command(script: str) -> str:
    run_script = "test" if script == "test" else f"run {script}"
    return f"""
    if [ ! -f package.json ]; then
      echo "No package.json found in this project directory."
      exit 0
    fi

    if node -e "const s=require('./package.json').scripts||{{}}; process.exit(s['{script}'] ? 0 : 1)"; then
      if [ -f pnpm-lock.yaml ]; then
        pnpm {run_script}
      elif [ -f yarn.lock ]; then
        yarn {run_script}
      else
        npm {run_script}
      fi
    else
      echo "No {script} script found."
    fi
    """


def _python_install_command() -> str:
    return """
    python -m pip install --upgrade pip

    if [ -f requirements.txt ]; then
      python -m pip install -r requirements.txt
    fi

    if [ -f setup.py ] || [ -f setup.cfg ]; then
      python -m pip install -e . || python -m pip install .
    elif [ -f pyproject.toml ] && grep -Eq '^\\[project\\]|^\\[tool\\.poetry\\]' pyproject.toml; then
      python -m pip install -e . || python -m pip install .
    elif [ -f pyproject.toml ]; then
      echo "pyproject.toml does not define an installable package; skipping package install."
    fi

    if [ -f Pipfile ]; then
      python -m pip install pipenv
      pipenv install --dev --deploy || pipenv install --dev
    fi

    python -m pip install pytest
    """


def _python_test_command() -> str:
    return """
    if [ -d tests ] || find . -maxdepth 3 \\( -name 'test_*.py' -o -name '*_test.py' \\) | grep -q .; then
      if [ -f Pipfile ]; then
        pipenv run pytest || status=$?
      else
        pytest || status=$?
      fi
      if [ "${status:-0}" -eq 5 ]; then
        echo "No pytest tests collected."
        exit 0
      fi
      exit "${status:-0}"
    else
      echo "No Python tests found."
    fi
    """


def _java_test_command() -> str:
    return """
    chmod +x ./mvnw ./gradlew 2>/dev/null || true

    if [ -x ./mvnw ]; then
      ./mvnw -B test
    elif [ -f pom.xml ]; then
      mvn -B test
    elif [ -x ./gradlew ]; then
      ./gradlew test
    elif [ -f build.gradle ] || [ -f build.gradle.kts ] || [ -f settings.gradle ] || [ -f settings.gradle.kts ]; then
      gradle test
    else
      echo "No Maven or Gradle build file found."
    fi
    """


def _docker_validate_command() -> str:
    return """
    if [ -f Dockerfile ]; then
      docker build -t ai-generated-app .
    elif [ -f docker-compose.yml ] || [ -f docker-compose.yaml ] || [ -f compose.yml ] || [ -f compose.yaml ]; then
      docker compose config
    else
      echo "No Dockerfile or Compose file found."
    fi
    """


def _validated(template: str) -> str:
    workflow = dedent(template).strip() + "\n"
    _validate_yaml(workflow)
    return workflow


def _indent_shell(command: str, spaces: int = 10) -> str:
    prefix = " " * spaces
    return "\n".join(f"{prefix}{line}" for line in dedent(command).strip().splitlines())


def _working_directory_line(project_dir: str) -> str:
    if project_dir == ".":
        return ""
    return f"        working-directory: {_yaml_quote(project_dir)}\n"


def _yaml_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _display_dir(project_dir: str) -> str:
    return "repository root" if project_dir == "." else project_dir


def _project_dir(stack: Mapping[str, Any]) -> str:
    value = str(stack.get("project_dir") or stack.get("path") or ".").strip().replace("\\", "/")
    return value.strip("/") or "."


def _detected_projects(stack: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw_projects = stack.get("detected_projects")
    if isinstance(raw_projects, list) and raw_projects:
        return [project for project in raw_projects if isinstance(project, Mapping)]

    recommended = str(stack.get("recommended_workflow") or "")
    inferred_type = {
        "node-ci": "node",
        "python-ci": "python",
        "java-ci": "java",
        "docker-ci": "docker",
    }.get(recommended)
    if not inferred_type:
        return []
    return [
        {
            "type": inferred_type,
            "path": _project_dir(stack),
            "framework": str(stack.get("framework") or inferred_type),
            "package_manager": str(stack.get("package_manager") or "unknown"),
        }
    ]


def _job_id(prefix: str, project_dir: str) -> str:
    if project_dir == ".":
        return prefix
    suffix = re.sub(r"[^a-z0-9]+", "-", project_dir.lower()).strip("-")
    return f"{prefix}-{suffix or 'project'}"


def _validate_yaml(workflow: str) -> None:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to validate generated workflow YAML.") from exc

    loaded = yaml.safe_load(workflow)
    if not isinstance(loaded, dict) or "jobs" not in loaded or "on" not in loaded:
        raise ValueError("Generated workflow YAML must contain 'on' and 'jobs' sections.")
