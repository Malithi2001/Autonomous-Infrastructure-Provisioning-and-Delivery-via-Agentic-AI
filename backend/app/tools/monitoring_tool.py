"""
Monitoring Tool — System metrics and service health checks.
All functions return real data (psutil + httpx). No placeholders.
"""
from __future__ import annotations

import time

import httpx
import psutil

from app.core.logging import logger


def get_system_metrics() -> str:
    """Return current system resource metrics."""
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        net = psutil.net_io_counters()
        load = psutil.getloadavg()

        return (
            f"📊 System Metrics\n"
            f"  CPU Usage    : {cpu:.1f}%\n"
            f"  Load Avg     : {load[0]:.2f} / {load[1]:.2f} / {load[2]:.2f} (1m/5m/15m)\n"
            f"  Memory       : {mem.percent:.1f}% used "
            f"({mem.used // 1024**2} MB / {mem.total // 1024**2} MB)\n"
            f"  Disk         : {disk.percent:.1f}% used "
            f"({disk.used // 1024**3:.1f} GB / {disk.total // 1024**3:.1f} GB)\n"
            f"  Network I/O  : ↑ {net.bytes_sent // 1024**2} MB sent "
            f"| ↓ {net.bytes_recv // 1024**2} MB recv"
        )
    except Exception as e:
        logger.error("monitoring.metrics.error", error=str(e))
        return f"Error reading system metrics: {e}"


def get_service_health(url: str, service_name: str = "service", timeout: int = 10) -> str:
    """
    Perform an HTTP health check on a service endpoint.
    Returns status, response time, and HTTP status code.
    """
    try:
        start = time.monotonic()
        response = httpx.get(url, timeout=timeout, follow_redirects=True)
        elapsed_ms = (time.monotonic() - start) * 1000
        emoji = "✅" if response.status_code < 400 else "❌"
        return (
            f"{emoji} {service_name} health check\n"
            f"  URL         : {url}\n"
            f"  HTTP Status : {response.status_code}\n"
            f"  Response    : {elapsed_ms:.0f} ms\n"
            f"  Result      : {'Healthy' if response.status_code < 400 else 'Unhealthy'}"
        )
    except httpx.ConnectError:
        return f"❌ {service_name}: Connection refused — service may be down at {url}"
    except httpx.TimeoutException:
        return f"❌ {service_name}: Request timed out after {timeout}s at {url}"
    except Exception as e:
        return f"❌ {service_name}: Unexpected error — {e}"


def get_process_list(sort_by: str = "cpu", limit: int = 10) -> str:
    """
    Return the top processes sorted by CPU or memory usage.

    Args:
        sort_by: "cpu" or "memory"
        limit:   number of processes to return (max 20)
    """
    try:
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
            try:
                procs.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        key = "memory_percent" if sort_by == "memory" else "cpu_percent"
        procs.sort(key=lambda p: p.get(key) or 0, reverse=True)

        lines = [f"{'PID':>7}  {'CPU%':>6}  {'MEM%':>6}  STATUS    NAME"]
        lines.append("-" * 50)
        for p in procs[: min(limit, 20)]:
            lines.append(
                f"{p['pid']:>7}  {(p['cpu_percent'] or 0):>5.1f}%  "
                f"{(p['memory_percent'] or 0):>5.1f}%  {p['status']:<9} {p['name']}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error("monitoring.process_list.error", error=str(e))
        return f"Error reading process list: {e}"


def check_multiple_services(urls: list[str], timeout: int = 5) -> str:
    """
    Check health of multiple service URLs in parallel.

    Args:
        urls:    list of HTTP/HTTPS URLs
        timeout: per-request timeout in seconds
    """
    if not urls:
        return "No URLs provided."
    lines = []
    with httpx.Client(timeout=timeout) as client:
        for url in urls[:10]:  # cap at 10
            try:
                start = time.monotonic()
                r = client.get(url, follow_redirects=True)
                ms = (time.monotonic() - start) * 1000
                emoji = "✅" if r.status_code < 400 else "❌"
                lines.append(f"{emoji} {r.status_code} ({ms:.0f}ms) {url}")
            except httpx.ConnectError:
                lines.append(f"❌ CONN_REFUSED {url}")
            except httpx.TimeoutException:
                lines.append(f"⏱️  TIMEOUT ({timeout}s) {url}")
            except Exception as e:
                lines.append(f"❌ ERROR {url} — {e}")
    return "\n".join(lines)
