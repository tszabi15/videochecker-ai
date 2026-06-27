from celery import Celery
from app.config import settings

celery_app = Celery(
    "videochecker_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.pipeline"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)
