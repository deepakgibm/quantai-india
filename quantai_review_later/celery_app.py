from celery import Celery
from config import settings

celery_app = Celery(
    "algobot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
)

# Auto-discover tasks
# We will create a 'tasks' package
celery_app.autodiscover_tasks(["tasks"])
