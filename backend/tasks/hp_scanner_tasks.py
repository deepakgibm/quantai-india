from celery_app import celery_app
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.hp_scanner.compute_chunk")
def compute_chunk_task(tasks_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Celery task that computes indicators for a chunk of symbols and writes the
    results to Dragonfly.
    """
    from workers.indicator_worker import ComputeTask, compute_indicators_process
    from services.dragonfly_client import get_cache, CacheKeys, TTLPolicy
    
    results = []
    cache = get_cache()
    
    for data in tasks_data:
        symbol = data["symbol"]
        interval = data["interval"]
        candles = data["candles"]
        
        task = ComputeTask(
            symbol=symbol,
            interval=interval,
            candles=candles
        )
        
        try:
            res = compute_indicators_process(task)
            if res.snapshot:
                # Write to Dragonfly immediately on the worker
                cache.set(
                    CacheKeys.snapshot(symbol),
                    res.snapshot,
                    TTLPolicy.SNAPSHOT
                )
                cache.set(
                    CacheKeys.indicator(symbol, "1d"),
                    res.indicators,
                    TTLPolicy.INDICATOR
                )
                
                results.append({
                    "symbol": res.symbol,
                    "snapshot": res.snapshot,
                    "indicators": res.indicators
                })
        except Exception as e:
            logger.error(f"Error computing indicators for {symbol} on worker: {e}")
            
    return results
