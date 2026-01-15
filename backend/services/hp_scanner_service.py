"""
High-Performance Scanner Service (v3)
Uses Memcached for <50ms reads, multiprocessing for computations.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading
import time

from services.dragonfly_client import (
    get_cache, cache_set, cache_get,
    CacheKeys, TTLPolicy
)

logger = logging.getLogger(__name__)


class HPScannerService:
    """
    High-Performance Scanner Service.
    
    Architecture:
    - Background thread runs scan cycles
    - Multiprocessing worker computes indicators
    - Results written to Memcached
    - API reads only from cache (no computation)
    """
    
    def __init__(self):
        self._is_running = False
        self._scan_interval = 5  # seconds
        self._last_scan_time: Optional[datetime] = None
        self._scan_count = 0
        self._symbols: List[str] = []
        self._lock = threading.Lock()
        self._worker_thread: Optional[threading.Thread] = None
    
    async def start(self):
        """Start the HP scanner service."""
        from engine.state import get_state_manager
        
        if self._is_running:
            logger.warning("HP Scanner service already running")
            return
        
        self._is_running = True
        logger.info("Starting HP Scanner Service (Memcached-backed)")
        
        # Load symbols from database
        await self._load_symbols()
        
        # Warm up state manager with 1day candles
        if self._symbols:
            logger.info("Warming up state manager with historical data...")
            # Use run_in_executor to avoid blocking event loop during DB fetch
            await asyncio.get_event_loop().run_in_executor(
                None,
                get_state_manager().warm_up_from_db,
                self._symbols,
                "1day"
            )
        
        # Start background worker thread
        self._worker_thread = threading.Thread(
            target=self._run_worker_loop,
            daemon=True,
            name="HPScannerWorker"
        )
        self._worker_thread.start()

    async def stop(self):
        """Stop the HP scanner service."""
        if not self._is_running:
            return
        
        logger.info("Stopping HP Scanner Service")
        self._is_running = False
        
        # Stop worker thread
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
            self._worker_thread = None
        
        # Stop indicator worker
        from workers.indicator_worker import stop_indicator_workers
        stop_indicator_workers()
        
        logger.info("HP Scanner Service stopped")

    async def _load_symbols(self):
        """Load Nifty 100 symbols from database for scanning."""
        from services.top_movers_service import NIFTY_100_SYMBOLS
        from database import AsyncSessionLocal
        from services.nifty500_fetcher import Nifty500Symbol
        from sqlalchemy import select
        
        try:
            async with AsyncSessionLocal() as session:
                # We prioritize the predefined NIFTY_100_SYMBOLS
                # but verify they exist in our master list to get metadata if needed.
                self._symbols = NIFTY_100_SYMBOLS
                logger.info(f"Loaded {len(self._symbols)} Nifty 100 symbols for HP scanning")
        except Exception as e:
            logger.error(f"Failed to load symbols for HP Scanner: {e}")
            # Fallback to hardcoded list if DB fails
            self._symbols = NIFTY_100_SYMBOLS[:20] 

    def _run_worker_loop(self):
        """Background worker loop (runs in separate thread)."""
        logger.info("HP Scanner worker loop started")
        
        while self._is_running:
            try:
                start = time.time()
                self._run_scan_cycle()
                elapsed = (time.time() - start) * 1000
                
                logger.info(
                    f"Scan cycle #{self._scan_count}: "
                    f"{len(self._symbols)} symbols in {elapsed:.0f}ms"
                )
                self._scan_count += 1
                
            except Exception as e:
                logger.error(f"Scan cycle error: {e}")
            
            # Sleep until next cycle
            time.sleep(self._scan_interval)
        
        logger.info("HP Scanner worker loop stopped")
    
    def _run_scan_cycle(self):
        """Execute one scan cycle."""
        from workers.indicator_worker import (
            get_indicator_worker, ComputeTask
        )
        from engine.state import get_state_manager
        
        if not self._symbols:
            return
        
        state_manager = get_state_manager()
        worker = get_indicator_worker()
        
        # Ensure worker is started
        if not worker._is_running:
            worker.start()
        
        # Build compute tasks
        tasks = []
        for symbol in self._symbols:
            symbol_state = state_manager.get_symbol(symbol)
            if not symbol_state:
                continue
            
            candles = symbol_state.get_candles("1day", 200)
            if len(candles) < 20:
                continue
            
            task = ComputeTask(
                symbol=symbol,
                interval="1day",
                candles=[{
                    'open': c.open,
                    'high': c.high,
                    'low': c.low,
                    'close': c.close,
                    'volume': c.volume
                } for c in candles]
            )
            tasks.append(task)
        
        if not tasks:
            return
        
        # Compute in parallel using multiprocessing
        results = worker.compute_batch(tasks)
        
        # Write results to cache
        cache = get_cache()
        all_snapshots = []
        momentum_data = []
        breakout_data = []
        reversal_data = []
        all_signals = []
        
        for result in results:
            if not result.snapshot:
                continue
            
            snapshot = result.snapshot
            symbol = result.symbol
            
            # Cache individual snapshot
            cache.set(
                CacheKeys.snapshot(symbol),
                snapshot,
                TTLPolicy.SNAPSHOT
            )
            
            # Cache indicators
            cache.set(
                CacheKeys.indicator(symbol, "1d"),
                result.indicators,
                TTLPolicy.INDICATOR
            )
            
            # Collect for aggregated caches
            all_snapshots.append(snapshot)
            
            # Categorize for scanner types
            change_pct = snapshot.get('change_pct', 0)
            signals = snapshot.get('signals', [])
            
            # Momentum
            momentum_data.append(snapshot)
            
            # Breakout (>2% move)
            if abs(change_pct) > 2.0:
                breakout_data.append(snapshot)
            
            # Reversal (RSI extremes)
            if 'RSI_OVERSOLD' in signals or 'RSI_OVERBOUGHT' in signals:
                reversal_data.append(snapshot)
            
            # Active signals
            if signals:
                all_signals.append({
                    'symbol': symbol,
                    'signals': signals,
                    'change_pct': change_pct,
                    'updated_at': snapshot.get('updated_at')
                })
        
        # Sort by change_pct for momentum
        momentum_data.sort(key=lambda x: abs(x.get('change_pct', 0)), reverse=True)
        breakout_data.sort(key=lambda x: abs(x.get('change_pct', 0)), reverse=True)
        
        # Cache aggregated results
        cache.set(CacheKeys.all_snapshots(), all_snapshots, TTLPolicy.SCANNER)
        cache.set(CacheKeys.momentum(), momentum_data, TTLPolicy.SCANNER)
        cache.set(CacheKeys.breakout(), breakout_data, TTLPolicy.SCANNER)
        cache.set(CacheKeys.reversal(), reversal_data, TTLPolicy.SCANNER)
        cache.set(CacheKeys.signals(), all_signals, TTLPolicy.SCANNER)
        
        self._scan_count += 1
        self._last_scan_time = datetime.now()
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status."""
        from services.memcached_client import cache_stats
        
        return {
            'is_running': self._is_running,
            'symbol_count': len(self._symbols),
            'scan_count': self._scan_count,
            'last_scan_time': self._last_scan_time.isoformat() if self._last_scan_time else None,
            'scan_interval': self._scan_interval,
            'cache_stats': cache_stats()
        }


# =============================================================================
# Singleton
# =============================================================================
_hp_scanner_service: Optional[HPScannerService] = None


def get_hp_scanner_service() -> HPScannerService:
    """Get the global HP scanner service instance."""
    global _hp_scanner_service
    if _hp_scanner_service is None:
        _hp_scanner_service = HPScannerService()
    return _hp_scanner_service


async def start_hp_scanner():
    """Start the HP scanner service."""
    service = get_hp_scanner_service()
    await service.start()


async def stop_hp_scanner():
    """Stop the HP scanner service."""
    service = get_hp_scanner_service()
    await service.stop()
