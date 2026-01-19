"""
Pre-Market Cache Warmer
Runs at 09:10 IST to populate Memcached before market open (09:15 IST).
"""

import asyncio
import logging
from datetime import datetime, time as dt_time
from typing import List, Dict, Any
import threading
import time

from services.dragonfly_client import (
    get_cache, CacheKeys, TTLPolicy
)

logger = logging.getLogger(__name__)


class CacheWarmer:
    """
    Pre-market cache warming service.
    
    Runs at 09:10 IST to:
    1. Load last N candles for all symbols
    2. Precompute indicators
    3. Populate Memcached before market opens at 09:15
    """
    
    WARMUP_TIME = dt_time(9, 10, 0)  # 09:10 IST
    MARKET_OPEN = dt_time(9, 15, 0)  # 09:15 IST
    MARKET_CLOSE = dt_time(15, 30, 0)  # 15:30 IST
    
    def __init__(self):
        self._is_running = False
        self._thread: threading.Thread = None
        self._last_warmup: datetime = None
        self._warmup_count = 0
    
    def start(self):
        """Start the cache warmer scheduler."""
        if self._is_running:
            return
        
        self._is_running = True
        self._thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="CacheWarmer"
        )
        self._thread.start()
        logger.info("Cache warmer scheduler started")
    
    def stop(self):
        """Stop the cache warmer."""
        self._is_running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Cache warmer stopped")
    
    def _scheduler_loop(self):
        """Scheduler loop - checks every minute for warmup time."""
        while self._is_running:
            now = datetime.now()
            current_time = now.time()
            
            # Check if it's warmup time (09:10) and we haven't warmed today
            if self._should_warmup(current_time, now):
                logger.info("Starting pre-market cache warm-up")
                self._run_warmup()
                self._last_warmup = now
                self._warmup_count += 1
            
            # Sleep for 30 seconds before next check
            time.sleep(30)
    
    def _should_warmup(self, current_time: dt_time, now: datetime) -> bool:
        """Check if we should run warmup."""
        # Within warmup window (09:10 - 09:14)
        if not (self.WARMUP_TIME <= current_time < self.MARKET_OPEN):
            return False
        
        # Haven't warmed up today
        if self._last_warmup and self._last_warmup.date() == now.date():
            return False
        
        return True
    
    def _run_warmup(self):
        """Execute the cache warm-up."""
        import psycopg2
        from config import settings
        from workers.indicator_worker import (
            get_indicator_worker, ComputeTask, start_indicator_workers
        )
        
        start = time.time()
        
        try:
            # Ensure worker is started
            start_indicator_workers()
            worker = get_indicator_worker()
            
            # Connect to database
            conn = psycopg2.connect(settings.SYNC_DATABASE_URL)
            cur = conn.cursor()
            
            # Get all symbols via instrument_master
            cur.execute("""
                SELECT DISTINCT im.symbol 
                FROM instrument_master im
                WHERE im.is_active = TRUE AND im.exchange = 'NSE' AND im.series = 'EQ'
                LIMIT 500
            """)
            symbols = [row[0] for row in cur.fetchall()]
            logger.info(f"Warming cache for {len(symbols)} symbols")
            
            # Build compute tasks
            tasks = []
            for symbol in symbols:
                # Fetch last 200 candles from stock_candle using new schema
                cur.execute("""
                    SELECT sc.candle_ts, sc.open, sc.high, sc.low, sc.close, sc.volume
                    FROM stock_candle sc
                    JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                    WHERE im.symbol = %s AND sc.timeframe = 1440
                    ORDER BY sc.candle_ts DESC
                    LIMIT 200
                """, (symbol,))
                
                rows = cur.fetchall()
                if len(rows) < 20:
                    continue
                
                # Reverse for chronological order
                candles = [
                    {
                        'open': float(r[1]),
                        'high': float(r[2]),
                        'low': float(r[3]),
                        'close': float(r[4]),
                        'volume': int(r[5])
                    }
                    for r in reversed(rows)
                ]
                
                tasks.append(ComputeTask(
                    symbol=symbol,
                    interval="1d",
                    candles=candles
                ))
            
            conn.close()
            
            if not tasks:
                logger.warning("No symbols to warm up")
                return
            
            # Compute in parallel
            logger.info(f"Computing indicators for {len(tasks)} symbols")
            results = worker.compute_batch(tasks)
            
            # Write to cache
            cache = get_cache()
            all_snapshots = []
            momentum_data = []
            
            for result in results:
                if not result.snapshot:
                    continue
                
                snapshot = result.snapshot
                symbol = result.symbol
                
                # Cache individual snapshot
                cache.set(
                    CacheKeys.snapshot(symbol),
                    snapshot,
                    TTLPolicy.SNAPSHOT * 10  # Longer TTL for warmup (50s)
                )
                
                # Cache indicators
                cache.set(
                    CacheKeys.indicator(symbol, "1d"),
                    result.indicators,
                    TTLPolicy.INDICATOR * 10
                )
                
                all_snapshots.append(snapshot)
                momentum_data.append(snapshot)
            
            # Sort and cache aggregated data
            momentum_data.sort(key=lambda x: abs(x.get('change_pct', 0)), reverse=True)
            
            cache.set(CacheKeys.all_snapshots(), all_snapshots, TTLPolicy.SCANNER * 10)
            cache.set(CacheKeys.momentum(), momentum_data, TTLPolicy.SCANNER * 10)
            
            # Mark warmup complete
            cache.set(CacheKeys.warmup_status(), {
                'time': datetime.now().isoformat(),
                'symbol_count': len(results),
                'status': 'complete'
            }, TTLPolicy.WARMUP)
            
            elapsed = time.time() - start
            logger.info(
                f"Cache warm-up complete: {len(results)} symbols in {elapsed:.1f}s"
            )
            
        except Exception as e:
            logger.error(f"Cache warm-up failed: {e}")
    
    def trigger_manual_warmup(self):
        """Trigger a manual cache warm-up."""
        threading.Thread(
            target=self._run_warmup,
            daemon=True
        ).start()
        return {"status": "warming", "message": "Manual warm-up triggered"}
    
    def get_status(self) -> Dict[str, Any]:
        """Get warmer status."""
        return {
            'is_running': self._is_running,
            'last_warmup': self._last_warmup.isoformat() if self._last_warmup else None,
            'warmup_count': self._warmup_count,
            'warmup_time': self.WARMUP_TIME.isoformat(),
            'market_open': self.MARKET_OPEN.isoformat()
        }


# =============================================================================
# Singleton
# =============================================================================
_cache_warmer: CacheWarmer = None


def get_cache_warmer() -> CacheWarmer:
    """Get the global cache warmer instance."""
    global _cache_warmer
    if _cache_warmer is None:
        _cache_warmer = CacheWarmer()
    return _cache_warmer


def start_cache_warmer():
    """Start the cache warmer."""
    warmer = get_cache_warmer()
    warmer.start()


def stop_cache_warmer():
    """Stop the cache warmer."""
    global _cache_warmer
    if _cache_warmer:
        _cache_warmer.stop()
        _cache_warmer = None
