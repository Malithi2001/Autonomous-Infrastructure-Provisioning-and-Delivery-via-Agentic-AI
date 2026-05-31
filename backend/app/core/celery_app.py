"""Celery application used by docker-compose worker and Flower services."""
from __future__ import annotations

from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "devops_assistant",
    broker=settings.CELERY_BROKER_URL or settings.REDIS_URL,
    backend=settings.CELERY_RESULT_BACKEND or settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

# Celery's `-A app.core.celery_app` autodiscovery looks for `app`.
app = celery_app
