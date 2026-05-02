"""
Bot API Router

REST endpoints for the signal generation bot.
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/run")
async def start_bot_run(background_tasks: BackgroundTasks):
    """
    Start a new bot pipeline run.
    Returns immediately with a run_id for status polling.
    """
    from services.bot.bot_orchestrator import get_bot_orchestrator

    orchestrator = get_bot_orchestrator()

    # Check if a run is already in progress
    last_id = orchestrator.get_last_run_id()
    if last_id:
        status = orchestrator.get_status(last_id)
        if status and status.status not in ("COMPLETED", "ERROR", "IDLE"):
            return {
                "status": "already_running",
                "run_id": last_id,
                "message": "A bot run is already in progress. Poll /api/bot/status/{run_id} for updates.",
            }

    # Create a wrapper to run the async orchestrator in the background
    run_id_holder = {"id": None}

    async def _run_bot():
        run_id = await orchestrator.run(history_days=90)
        run_id_holder["id"] = run_id

    # We need to run this as a background asyncio task
    loop = asyncio.get_event_loop()
    task = loop.create_task(orchestrator.run(history_days=90))

    # Give it a moment to register the run_id
    await asyncio.sleep(0.3)

    # Get the latest run_id
    latest_id = orchestrator.get_last_run_id()
    if not latest_id:
        # The task hasn't registered yet; return a pending status
        return {
            "status": "starting",
            "message": "Bot is starting. Retry in 1 second.",
        }

    return {
        "status": "started",
        "run_id": latest_id,
        "message": "Bot pipeline started. Poll /api/bot/status/{run_id} for progress.",
    }


@router.get("/status/{run_id}")
async def get_bot_status(run_id: str):
    """Get current status and progress of a bot run."""
    from services.bot.bot_orchestrator import get_bot_orchestrator

    orchestrator = get_bot_orchestrator()
    status = orchestrator.get_status(run_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    return {"status": "success", "data": status.to_dict()}


@router.get("/results/{run_id}")
async def get_bot_results(run_id: str):
    """Get final results of a completed bot run."""
    from services.bot.bot_orchestrator import get_bot_orchestrator

    orchestrator = get_bot_orchestrator()
    status = orchestrator.get_status(run_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    if status.status not in ("COMPLETED",):
        return {
            "status": "pending",
            "message": f"Run is still in progress: {status.current_step_label}",
            "progress": status.progress_pct,
        }

    result = orchestrator.get_result(run_id)
    if not result:
        raise HTTPException(status_code=500, detail="Results not available")

    return {"status": "success", "data": result.to_dict()}


@router.get("/last-run")
async def get_last_run():
    """Get status and results of the most recent bot run."""
    from services.bot.bot_orchestrator import get_bot_orchestrator

    orchestrator = get_bot_orchestrator()
    last_id = orchestrator.get_last_run_id()

    if not last_id:
        return {
            "status": "no_runs",
            "message": "No bot runs found. Click 'Start Bot' to begin.",
        }

    status = orchestrator.get_status(last_id)
    result = orchestrator.get_result(last_id)

    response: dict = {
        "status": "success",
        "run_id": last_id,
        "run_status": status.to_dict() if status else None,
    }

    if result:
        response["data"] = result.to_dict()

    return response


@router.get("/history")
async def get_bot_history(limit: int = 10):
    """
    Get recent bot run history from the database.
    
    Args:
        limit: Number of runs to return (default 10, max 50)
    """
    from database import SessionLocal
    from models_bot import BotRun

    limit = min(limit, 50)

    db = SessionLocal()
    try:
        runs = (
            db.query(BotRun)
            .order_by(BotRun.started_at.desc())
            .limit(limit)
            .all()
        )

        return {
            "status": "success",
            "data": [
                {
                    "run_id": r.run_id,
                    "status": r.status,
                    "market_trend": r.market_trend.get("trend") if r.market_trend else None,
                    "buy_count": r.buy_count,
                    "sell_count": r.sell_count,
                    "triggered_by": r.triggered_by,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                    "execution_time": r.summary.get("execution_time_seconds") if r.summary else None,
                    "pcr_source": r.summary.get("data_sources", {}).get("pcr") if r.summary else None,
                }
                for r in runs
            ],
            "total": len(runs),
        }
    except Exception as e:
        logger.error(f"Failed to fetch bot history: {e}")
        return {"status": "success", "data": [], "total": 0}
    finally:
        db.close()


@router.get("/scheduler-status")
async def get_scheduler_status():
    """Get the current bot scheduler configuration."""
    from config import settings

    return {
        "status": "success",
        "data": {
            "enabled": settings.BOT_SCHEDULER_ENABLED,
            "morning_run": settings.BOT_SCHEDULE_MORNING,
            "close_run": settings.BOT_SCHEDULE_CLOSE,
            "telegram_configured": bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID),
        },
    }
