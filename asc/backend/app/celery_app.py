"""Celery configuration for background task processing."""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "asc",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.workflow_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_max_tasks_per_child=10,
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, name="health_check")
def health_check(self):
    """Simple health check task."""
    return {"status": "healthy", "task_id": self.request.id}