"""Generate GitHub Actions CI workflows from repository stack detection."""
from __future__ import annotations

from collections.abc import Mapping
from textwrap import dedent
from typing import Any


WORKFLOW_PATH = ".github/workflows/ai-generated-ci.yml"


def generate_workflow(stack: Mapping[str, Any]) -> str:
    """Return a GitHub Actions workflow YAML string for a detected stack."""
    recommended = stack.get("recommended_workflow")
    if recommended == "node-ci":
        return generate_node_workflow(package_manager=str(stack.get("package_manager") or "npm"))
    if recommended == "python-ci":
        return generate_python_workflow()
    if recommended == "java-ci":
        return generate_java_workflow()
    if recommended == "docker-ci":
        return generate_docker_workflow()
    return _validated(
        """
        name: AI Generated CI

        'on':
          push:
            branches: [main]
          pull_request:

        jobs:
          generic-ci:
            runs-on: ubuntu-latest
            steps:
              - name: Checkout repository
                uses: actions/checkout@v4

              - name: Inspect repository
                run: |
                  echo "No specific stack detected."
                  find . -maxdepth 2 -type f | sort
        """
    )


def generate_node_workflow(package_manager: str = "npm") -> str:
    package_manager = package_manager if package_manager in {"npm", "pnpm", "yarn"} else "npm"
    install_command = _node_install_command(package_manager)
    test_command = _node_script_command(package_manager, "test")
    build_command = _node_script_command(package_manager, "build")

    return _validated(
        f"""
        name: AI Generated Node CI

        'on':
          push:
            branches: [main]
          pull_request:

        jobs:
          node-ci:
            runs-on: ubuntu-latest
            steps:
              - name: Checkout repository
                uses: actions/checkout@v4

              - name: Set up Node.js
                uses: actions/setup-node@v4
                with:
                  node-version: 20

              - name: Enable package manager shims
                run: corepack enable

              - name: Install dependencies
                run: |
{install_command}

              - name: Run tests
                run: |
{test_command}

              - name: Build
                run: |
{build_command}
        """
    )


def generate_python_workflow() -> str:
    return _validated(
        """
        name: AI Generated Python CI

        'on':
          push:
            branches: [main]
          pull_request:

        jobs:
          python-ci:
            runs-on: ubuntu-latest
            steps:
              - name: Checkout repository
                uses: actions/checkout@v4

              - name: Set up Python
                uses: actions/setup-python@v5
                with:
                  python-version: '3.11'

              - name: Install dependencies
                run: |
                  python -m pip install --upgrade pip
                  if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
                  pip install pytest

              - name: Run tests
                run: |
                  if [ -d tests ]; then
                    pytest || status=$?
                    if [ "${status:-0}" -eq 5 ]; then
                      echo "No pytest tests collected."
                      exit 0
                    fi
                    exit "${status:-0}"
                  else
                    echo "No tests folder found."
                  fi
        """
    )


def generate_java_workflow() -> str:
    return _validated(
        """
        name: AI Generated Java CI

        'on':
          push:
            branches: [main]
          pull_request:

        jobs:
          java-ci:
            runs-on: ubuntu-latest
            steps:
              - name: Checkout repository
                uses: actions/checkout@v4

              - name: Set up Java
                uses: actions/setup-java@v4
                with:
                  distribution: temurin
                  java-version: 17

              - name: Run Maven tests
                run: mvn test
        """
    )


def generate_docker_workflow() -> str:
    return _validated(
        """
        name: AI Generated Docker CI

        'on':
          push:
            branches: [main]
          pull_request:

        jobs:
          docker-ci:
            runs-on: ubuntu-latest
            steps:
              - name: Checkout repository
                uses: actions/checkout@v4

              - name: Build Docker image
                run: docker build -t ai-generated-app .
        """
    )


def _validated(template: str) -> str:
    workflow = dedent(template).strip() + "\n"
    _validate_yaml(workflow)
    return workflow


def _indent_shell(command: str) -> str:
    return "\n".join(f"                  {line}" for line in dedent(command).strip().splitlines())


def _node_install_command(package_manager: str) -> str:
    if package_manager == "pnpm":
        command = "pnpm install --frozen-lockfile"
    elif package_manager == "yarn":
        command = "yarn install --frozen-lockfile"
    else:
        command = """
        if [ -f package-lock.json ]; then
          npm ci
        else
          npm install
        fi
        """
    return _indent_shell(command)


def _node_script_command(package_manager: str, script: str) -> str:
    run_command = f"{package_manager} run {script}" if script != "test" else f"{package_manager} test"
    command = f"""
    if node -e "const s=require('./package.json').scripts||{{}}; process.exit(s['{script}'] ? 0 : 1)"; then
      {run_command}
    else
      echo "No {script} script found."
    fi
    """
    return _indent_shell(command)


def _validate_yaml(workflow: str) -> None:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to validate generated workflow YAML.") from exc

    loaded = yaml.safe_load(workflow)
    if not isinstance(loaded, dict) or "jobs" not in loaded or "on" not in loaded:
        raise ValueError("Generated workflow YAML must contain 'on' and 'jobs' sections.")
