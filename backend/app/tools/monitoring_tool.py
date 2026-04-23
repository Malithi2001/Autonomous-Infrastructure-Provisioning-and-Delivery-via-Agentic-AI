"""
Monitoring Tool — System metrics and service health checks.
"""
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

        return (
            f"📊 System Metrics\n"
            f"  CPU Usage    : {cpu:.1f}%\n"
            f"  Memory       : {mem.percent:.1f}% used ({mem.used // 1024**2} MB / {mem.total // 1024**2} MB)\n"
            f"  Disk         : {disk.percent:.1f}% used ({disk.used // 1024**3:.1f} GB / {disk.total // 1024**3:.1f} GB)\n"
            f"  Network I/O  : ↑ {net.bytes_sent // 1024**2} MB sent | ↓ {net.bytes_recv // 1024**2} MB recv"
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
        import time
        start = time.monotonic()
        response = httpx.get(url, timeout=timeout, follow_redirects=True)
        elapsed_ms = (time.monotonic() - start) * 1000

        status_emoji = "✅" if response.status_code < 400 else "❌"
        return (
            f"{status_emoji} {service_name} health check\n"
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
