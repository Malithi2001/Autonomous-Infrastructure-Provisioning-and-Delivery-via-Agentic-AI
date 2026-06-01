"""Structured logging configuration."""
import logging
import sys
from typing import Any, Callable, MutableMapping, cast

import structlog

from app.core.config import settings


def setup_logging() -> None:
    """Configure structlog for structured JSON logging."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    renderer = (
        structlog.dev.ConsoleRenderer()
        if settings.DEBUG
        else structlog.processors.JSONRenderer()
    )
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        renderer,
    ]

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    structlog.configure(
        processors=cast(list[Callable[[Any, str, MutableMapping[str, Any]], Any]], processors),
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()
