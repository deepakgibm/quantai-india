"""
High-Performance Scanner Service (v3)
Uses Memcached for <50ms reads, multiprocessing for computations.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

from services.dragonfly_client import (
    get_cache, CacheKeys, TTLPolicy, cache_stats
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
        self._lock = asyncio.Lock()
        self._loop_task: Optional[asyncio.Task] = None
    
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
        
        # Start background loop
        self._loop_task = asyncio.create_task(self._run_loop())

    async def stop(self):
        """Stop the HP scanner service."""
        if not self._is_running:
            return
        
        logger.info("Stopping HP Scanner Service")
        self._is_running = False
        
        # Stop background loop
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
            self._loop_task = None
        
        # Stop indicator worker
        from workers.indicator_worker import stop_indicator_workers
        stop_indicator_workers()
        
        logger.info("HP Scanner Service stopped")

    async def _load_symbols(self):
        """Load symbols from database for scanning."""
        from utils.symbol_utils import get_nifty_symbols
        from database import AsyncSessionLocal
        
        try:
            async with AsyncSessionLocal() as session:
                self._symbols = get_nifty_symbols()
                logger.info(f"Loaded {len(self._symbols)} symbols for HP scanning")
        except Exception as e:
            logger.error(f"Failed to load symbols for HP Scanner: {e}")
            self._symbols = [] 

    async def _run_loop(self):
        """Background loop."""
        logger.info("HP Scanner loop started")
        
        while self._is_running:
            try:
                start = time.time()
                await self._run_scan_cycle_async()
                elapsed = (time.time() - start) * 1000
                
                if elapsed > 1000:
                    logger.info(
                        f"Scan cycle #{self._scan_count}: "
                        f"{len(self._symbols)} symbols in {elapsed:.0f}ms"
                    )
                self._scan_count += 1
                
            except Exception as e:
                logger.error(f"Scan cycle error: {e}")
            
            # Sleep until next cycle
            await asyncio.sleep(self._scan_interval)
        
        logger.info("HP Scanner loop stopped")
    
    async def _run_scan_cycle_async(self):
        """Execute one scan cycle asynchronously."""
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
        
        # Compute in parallel using multiprocessing (offloaded to thread pool to avoid blocking event loop)
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, worker.compute_batch, tasks)
        
        # Write results to cache in batch
        cache = get_cache()
        
        snapshot_mapping = {}
        indicator_mapping = {}
        
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
            
            # Batch individual outputs
            snapshot_mapping[CacheKeys.snapshot(symbol)] = snapshot
            indicator_mapping[CacheKeys.indicator(symbol, "1d")] = result.indicators
            
            # Collect for aggregated caches
            all_snapshots.append(snapshot)
            
            # Categorize for scanner types
            change_pct = snapshot.get('change_pct', 0)
            signals = snapshot.get('signals', [])
            
            momentum_data.append(snapshot)
            if abs(change_pct) > 2.0:
                breakout_data.append(snapshot)
            if 'RSI_OVERSOLD' in signals or 'RSI_OVERBOUGHT' in signals:
                reversal_data.append(snapshot)
            
            if signals:
                all_signals.append({
                    'symbol': symbol,
                    'signals': signals,
                    'change_pct': change_pct,
                    'updated_at': snapshot.get('updated_at')
                })
        
        # Batch cache writes
        if snapshot_mapping:
            await cache.mset_async(snapshot_mapping, TTLPolicy.SNAPSHOT)
        if indicator_mapping:
            await cache.mset_async(indicator_mapping, TTLPolicy.INDICATOR)
        
        # Sort data
        momentum_data.sort(key=lambda x: abs(x.get('change_pct', 0)), reverse=True)
        breakout_data.sort(key=lambda x: abs(x.get('change_pct', 0)), reverse=True)
        
        # Aggregated cache writes (standard mset)
        agg_mapping = {
            CacheKeys.all_snapshots(): all_snapshots,
            CacheKeys.momentum(): momentum_data,
            CacheKeys.breakout(): breakout_data,
            CacheKeys.reversal(): reversal_data,
            CacheKeys.signals(): all_signals
        }
        await cache.mset_async(agg_mapping, TTLPolicy.SCANNER)
        
        self._last_scan_time = datetime.now()
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status."""
        
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
