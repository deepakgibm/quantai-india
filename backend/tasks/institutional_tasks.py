from celery_app import celery_app
from etl.institutional_tracker import run_institutional_sync
from screener.services.screener_service import ScreenerService
import asyncio
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.institutional_tasks.sync_institutional_flows")
def sync_institutional_flows():
    """Periodically sync institutional flows from NSE."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(run_institutional_sync())

@celery_app.task(name="tasks.institutional_tasks.run_screener_scoring")
def run_screener_scoring(skip_financials: bool = False, top_n: int = None):
    """
    Run the full institutional screener scoring pipeline in the background.
    Offloads heavy stock analysis from the API event loop.
    """
    logger.info(f"Starting Background Screener Scoring (top_n={top_n}, skip_fin={skip_financials})")
    try:
        from database import AsyncSessionLocal
        
        async def main():
            async with AsyncSessionLocal() as session:
                service = ScreenerService(session)
                return await service.run_full_screening(
                    skip_financials=skip_financials,
                    top_n=top_n
                )

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        summary = loop.run_until_complete(main())
        logger.info("Background Screener Scoring completed successfully")
        return summary
    except Exception as e:
        logger.error(f"Background Screener Scoring failed: {e}", exc_info=True)
        raise
