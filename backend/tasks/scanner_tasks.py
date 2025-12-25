"""
Scanner Background Tasks
Celery tasks for running scanners in the background.
"""

from celery_app import celery_app
from typing import List, Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="tasks.scanner.run_full_scan")
def run_full_scan(self, indices: List[str], timeframe: str, strategies: List[str]) -> Dict[str, Any]:
    """
    Run a full scanner scan as a background task.
    
    Args:
        indices: List of indices to scan (e.g., ['NIFTY 50', 'NIFTY 100'])
        timeframe: Timeframe for scanning (e.g., '15m', '1d')
        strategies: List of strategy names to apply
    
    Returns:
        Dict with scan results and metadata
    """
    from core.scanner.scanner_engine import ScannerEngine
    import asyncio
    
    task_id = self.request.id
    logger.info(f"Starting background scan task {task_id}: {indices}, {timeframe}, {len(strategies)} strategies")
    
    start_time = datetime.now()
    
    try:
        scanner = ScannerEngine()
        
        # Run the async scan in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(
                scanner.run_scan(
                    indices=indices,
                    timeframe=timeframe,
                    strategies=strategies
                )
            )
        finally:
            loop.close()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return {
            "status": "completed",
            "task_id": task_id,
            "results": results,
            "total_stocks": len(set(r["symbol"] for r in results)) if results else 0,
            "signals_found": len(results),
            "duration_seconds": round(duration, 2),
            "completed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Background scan task {task_id} failed: {e}")
        return {
            "status": "failed",
            "task_id": task_id,
            "error": str(e),
            "duration_seconds": (datetime.now() - start_time).total_seconds()
        }


@celery_app.task(bind=True, name="tasks.scanner.compute_indicators")
def compute_indicators_task(self, interval: str = "1d", symbol_limit: int = None) -> Dict[str, Any]:
    """
    Compute and store precomputed indicators as a background task.
    
    Args:
        interval: Data interval (e.g., '1d', '15m')
        symbol_limit: Optional limit on number of symbols to process
    
    Returns:
        Dict with job statistics
    """
    from services.indicator_compute_service import get_indicator_service
    
    task_id = self.request.id
    logger.info(f"Starting indicator computation task {task_id}")
    
    try:
        service = get_indicator_service()
        result = service.compute_all(interval=interval, symbol_limit=symbol_limit)
        result["task_id"] = task_id
        result["status"] = "completed"
        return result
        
    except Exception as e:
        logger.error(f"Indicator computation task {task_id} failed: {e}")
        return {
            "status": "failed",
            "task_id": task_id,
            "error": str(e)
        }


@celery_app.task(name="tasks.scanner.refresh_momentum_cache")
def refresh_momentum_cache() -> Dict[str, Any]:
    """
    Refresh the momentum data cache.
    Called periodically to keep cache warm.
    """
    from services.db_data_fetcher import get_db_data_fetcher
    from services.cache import get_cache_manager
    
    logger.info("Refreshing momentum cache")
    
    try:
        db_fetcher = get_db_data_fetcher()
        db_data = db_fetcher.fetch_latest_data()
        
        if db_data:
            # Build response
            data = []
            for symbol, tick in db_data.items():
                data.append({
                    "symbol": tick.symbol,
                    "ltp": tick.ltp,
                    "prev_close": tick.prev_close,
                    "change_pct": tick.change_pct,
                    "momentum_score": max(5, min(95, 50 + int(tick.change_pct * 10))),
                    "bucket": tick.bucket,
                    "direction": tick.direction,
                    "source": "DB",
                    "confidence": "LOW",
                    "last_update": tick.timestamp
                })
            
            response = {
                "type": "bucket_update",
                "timestamp": datetime.now().isoformat(),
                "data": data,
                "status": {
                    "source": "DB",
                    "is_healthy": len(data) > 0,
                    "last_tick": datetime.now().isoformat(),
                    "stock_count": len(data),
                    "poll_interval": 60
                }
            }
            
            # Update cache
            cache = get_cache_manager()
            cache.set("quantai:momentum_data", response, ttl=60)
            
            return {"status": "success", "symbols_cached": len(data)}
        
        return {"status": "no_data"}
        
    except Exception as e:
        logger.error(f"Cache refresh failed: {e}")
        return {"status": "failed", "error": str(e)}


# Periodic task configuration (for Celery Beat)
# Add to celeryconfig.py:
#
# from celery.schedules import crontab
# 
# beat_schedule = {
#     'refresh-momentum-cache': {
#         'task': 'tasks.scanner.refresh_momentum_cache',
#         'schedule': 60.0,  # Every 60 seconds
#     },
#     'compute-daily-indicators': {
#         'task': 'tasks.scanner.compute_indicators',
#         'schedule': crontab(hour=4, minute=0),  # Daily at 4 AM
#         'args': ('1d',)
#     },
# }
