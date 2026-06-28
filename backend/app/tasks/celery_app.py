"""
Celery application configuration for VideoChecker AI workers.
"""

from celery import Celery
from app.config import settings

celery_app = Celery(
    "videochecker_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.pipeline"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Reliability: tasks are acknowledged only after completion
    task_acks_late=True,
    # Re-queue tasks if the worker is killed unexpectedly
    task_reject_on_worker_lost=True,
    # Process one task at a time per worker for predictable resource usage
    worker_prefetch_multiplier=1,
    # Prevent worker crash if Redis is slow to start
    broker_connection_retry_on_startup=True,
)
