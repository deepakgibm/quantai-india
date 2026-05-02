"""
Celery Application Factory — QuantAI India

Uses DragonflyDB (Redis-compatible) as both broker and result backend.
Configuration is pulled from config.py which reads from environment/dotenv.
"""

from celery import Celery
from celery.schedules import crontab
from config import settings

# Create Celery application
celery_app = Celery(
    "quantai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "tasks.ml_tasks",
        "tasks.backtest_tasks",
        "tasks.institutional_tasks",
        "tasks.bot_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    
    # Time limits (seconds)
    task_soft_time_limit=300,   # 5 min soft limit (raises SoftTimeLimitExceeded)
    task_time_limit=600,        # 10 min hard kill
    
    # Worker settings
    worker_prefetch_multiplier=1,      # Fair scheduling (don't prefetch too many)
    worker_max_tasks_per_child=50,     # Restart worker after 50 tasks (prevent memory leaks)
    worker_max_memory_per_child=512_000,  # 512MB per worker process
    
    # Result settings
    result_expires=3600,        # Results expire after 1 hour
    
    # Task tracking
    task_track_started=True,    # Track when tasks start (not just pending/success/failure)
    task_acks_late=True,        # Ack only after task completes (prevents task loss on crash)
    
    # Timezone
    timezone="Asia/Kolkata",
    enable_utc=True,
    
    # Task Routing
    task_routes={
        "tasks.ml_tasks.train_model": {"queue": "ml"},
        "tasks.backtest_tasks.run_backtest": {"queue": "backtest"},
    },
    
    # Retry policy for broker connection
    broker_connection_retry_on_startup=True,
)

# Optional: periodic tasks (Celery Beat schedule)
celery_app.conf.beat_schedule = {
    "retrain-models-daily": {
        "task": "tasks.ml_tasks.train_model",
        "schedule": 86400.0, # seconds = 1 day
        "args": (10, 64),
    },
    "sync-institutional-flows-daily": {
        "task": "tasks.institutional_tasks.sync_institutional_flows",
        "schedule": 43200.0, # Wait until 18:00 IST logic handled in task if needed, but 12h interval for safety
    },
    "run-signal-bot-morning": {
        "task": "tasks.bot_tasks.run_signal_bot",
        "schedule": crontab(hour=9, minute=20),  # 9:20 AM IST — after market opens
    },
    "run-signal-bot-close": {
        "task": "tasks.bot_tasks.run_signal_bot",
        "schedule": crontab(hour=15, minute=40),  # 3:40 PM IST — after market closes
    },
}
