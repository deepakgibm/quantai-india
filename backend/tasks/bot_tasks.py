"""
Bot Celery Tasks

Scheduled tasks for auto-running the signal bot pipeline.
Integrates with Celery Beat for cron-based scheduling.
"""

import logging
import asyncio
from celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="tasks.bot_tasks.run_signal_bot",
    bind=True,
    max_retries=1,
    soft_time_limit=300,
    time_limit=600,
)
def run_signal_bot(self):
    """
    Execute the signal bot pipeline as a Celery task.
    
    Designed for Celery Beat scheduling:
    - Morning run at 9:20 AM IST (after market opens)
    - Evening run at 3:40 PM IST (after market closes)
    
    Uses asyncio.run() since Celery workers are synchronous.
    """
    from config import settings

    if not getattr(settings, "BOT_SCHEDULER_ENABLED", True):
        logger.info("Bot scheduler is disabled via config. Skipping.")
        return {"status": "skipped", "reason": "scheduler_disabled"}

    logger.info("🤖 Scheduled bot run starting...")

    try:
        result = asyncio.run(_execute_bot_run())
        logger.info(f"🤖 Scheduled bot run completed: {result}")
        return result
    except Exception as e:
        logger.error(f"🤖 Scheduled bot run failed: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60)


async def _execute_bot_run():
    """Async wrapper for the bot orchestrator pipeline."""
    from services.bot.bot_orchestrator import get_bot_orchestrator

    orchestrator = get_bot_orchestrator()

    # Check if already running
    last_id = orchestrator.get_last_run_id()
    if last_id:
        status = orchestrator.get_status(last_id)
        if status and status.status not in ("COMPLETED", "ERROR", "IDLE"):
            return {
                "status": "skipped",
                "reason": "already_running",
                "run_id": last_id,
            }

    run_id = await orchestrator.run(history_days=270, triggered_by="scheduler")
    status = orchestrator.get_status(run_id)

    return {
        "status": "completed" if status and status.status == "COMPLETED" else "error",
        "run_id": run_id,
        "triggered_by": "scheduler",
    }
