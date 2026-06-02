"""
Docker Tool — LangChain tool functions for Docker container management.
Uses the Docker SDK for Python.
"""
from typing import Any

import docker
from docker.errors import DockerException, NotFound, APIError

from app.core.logging import logger

_client = None
_client_checked = False


def _check_client():
    global _client, _client_checked
    if not _client_checked:
        _client_checked = True
        try:
            _client = docker.from_env(timeout=3)
        except DockerException:
            _client = None
            logger.warning("docker.client.unavailable", detail="Docker socket not accessible.")
    if _client is None:
        raise RuntimeError("Docker client is not available. Ensure Docker is running and the socket is mounted.")
    return _client


# ── Read Operations ───────────────────────────────────────────────────────────

def list_containers(all_containers: bool = False) -> str:
    """List Docker containers."""
    docker_client = _check_client()
    try:
        containers = docker_client.containers.list(all=all_containers)
        if not containers:
            return "No containers found."
        rows = []
        for c in containers:
            ports = ", ".join(
                f"{h[0]['HostPort']}->{p}" for p, h in (c.ports or {}).items() if h
            ) or "none"
            image = c.image.tags[0] if c.image.tags else "unknown"
            rows.append(f"- [{c.status}] {c.name} (image: {image}, ports: {ports})")
        return "\n".join(rows)
    except APIError as e:
        logger.error("docker.list_containers.error", error=str(e))
        return f"Error listing containers: {e}"


def get_container_logs(container_name: str, tail_lines: int = 100) -> str:
    """Fetch container logs."""
    docker_client = _check_client()
    try:
        container = docker_client.containers.get(container_name)
        logs = container.logs(tail=tail_lines, timestamps=True).decode("utf-8")
        return logs or "(no logs available)"
    except NotFound:
        return f"Container '{container_name}' not found."
    except APIError as e:
        return f"Error fetching logs: {e}"


# ── Write Operations (elevated risk) ─────────────────────────────────────────

def restart_container(container_name: str) -> str:
    """Restart a container — used in self-healing workflows."""
    docker_client = _check_client()
    try:
        container = docker_client.containers.get(container_name)
        container.restart(timeout=30)
        logger.info("docker.restart", container=container_name)
        return f"✅ Container '{container_name}' restarted successfully."
    except NotFound:
        return f"Container '{container_name}' not found."
    except APIError as e:
        return f"Error restarting container: {e}"


def start_container(container_name: str) -> str:
    """Start a stopped container."""
    docker_client = _check_client()
    try:
        container = docker_client.containers.get(container_name)
        container.start()
        logger.info("docker.start", container=container_name)
        return f"✅ Container '{container_name}' started."
    except NotFound:
        return f"Container '{container_name}' not found."
    except APIError as e:
        return f"Error starting container: {e}"


def stop_container(container_name: str, timeout: int = 10) -> str:
    """Stop a running container."""
    docker_client = _check_client()
    try:
        container = docker_client.containers.get(container_name)
        container.stop(timeout=timeout)
        logger.info("docker.stop", container=container_name)
        return f"✅ Container '{container_name}' stopped."
    except NotFound:
        return f"Container '{container_name}' not found."
    except APIError as e:
        return f"Error stopping container: {e}"


def run_container(
    image: str,
    name: str,
    ports: dict[str, Any] | None = None,
    environment: dict[str, Any] | None = None,
    detach: bool = True,
) -> str:
    """Run a new container from an image."""
    docker_client = _check_client()
    try:
        container = docker_client.containers.run(
            image=image,
            name=name,
            ports=ports or {},
            environment=environment or {},
            detach=detach,
            remove=False,
        )
        logger.info("docker.run", image=image, name=name)
        return f"✅ Container '{name}' started from image '{image}'. ID: {container.short_id}"
    except APIError as e:
        return f"Error running container: {e}"
