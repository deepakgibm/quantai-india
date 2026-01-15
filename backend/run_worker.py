"""
Standalone HP Scanner Worker Process
Runs independently from FastAPI to avoid GIL contention.

Usage:
    python hp_scanner_worker.py

This process:
1. Loads symbols from database
2. Computes indicators using multiprocessing pool
3. Writes results to Dragonfly (Redis-compatible, 25x faster)
4. Runs continuously with 5-second scan cycles

The FastAPI process reads from Dragonfly only (no computation).

Prerequisites:
    docker run -d --name dragonfly -p 6379:6379 docker.dragonflydb.io/dragonflydb/dragonfly
"""


import os
import sys
import time
import signal
import logging
from datetime import datetime
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.dragonfly_client import (
    get_cache, CacheKeys, TTLPolicy
)
from workers.indicator_worker import (
    get_indicator_worker, ComputeTask, start_indicator_workers
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("HPScannerWorker")

# Global flag for graceful shutdown
_running = True


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global _running
    logger.info("Shutdown signal received")
    _running = False


def load_symbols() -> List[str]:
    """Load symbols from database."""
    import psycopg2
    from config import settings
    
    try:
        conn = psycopg2.connect(settings.SYNC_DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT symbol FROM stock_candles LIMIT 200")
        symbols = [row[0] for row in cur.fetchall()]
        conn.close()
        logger.info(f"Loaded {len(symbols)} symbols from database")
        return symbols
    except Exception as e:
        logger.error(f"Failed to load symbols: {e}")
        return []


def load_candles(symbols: List[str]) -> Dict[str, List[Dict]]:
    """Load candles for all symbols using batch query (replaces N+1 pattern)."""
    import psycopg2
    from config import settings
    
    candles_map = {}
    
    if not symbols:
        return candles_map
    
    try:
        conn = psycopg2.connect(settings.SYNC_DATABASE_URL)
        cur = conn.cursor()
        
        # Single batch query for ALL symbols at once - replaces N+1 pattern
        # This reduces 200 round trips to 1 round trip
        cur.execute("""
            SELECT symbol, timestamp, "open", high, low, "close", volume
            FROM stock_candles
            WHERE symbol = ANY(%s) AND timeframe = '1d'
            ORDER BY symbol, timestamp DESC
        """, (symbols,))
        
        rows = cur.fetchall()
        conn.close()
        
        # Group rows by symbol
        from collections import defaultdict
        symbol_rows = defaultdict(list)
        for row in rows:
            symbol_rows[row[0]].append(row)
        
        # Process each symbol's rows (limit to 200 most recent, reverse for chronological order)
        for symbol, sym_rows in symbol_rows.items():
            # Take first 200 (already ordered DESC, so these are most recent)
            recent_rows = sym_rows[:200]
            if len(recent_rows) >= 20:
                candles_map[symbol] = [
                    {
                        'open': float(r[2]),
                        'high': float(r[3]),
                        'low': float(r[4]),
                        'close': float(r[5]),
                        'volume': int(r[6])
                    }
                    for r in reversed(recent_rows)  # Reverse to chronological order
                ]
        
        logger.info(f"Loaded candles for {len(candles_map)} symbols using batch query (1 round trip)")
        return candles_map
        
    except Exception as e:
        logger.error(f"Failed to load candles: {e}")
        return {}


def run_scan_cycle(symbols: List[str], candles_map: Dict[str, List[Dict]]):
    """Execute one scan cycle."""
    start = time.time()
    
    worker = get_indicator_worker()
    
    # Build compute tasks
    tasks = []
    for symbol in symbols:
        candles = candles_map.get(symbol)
        if candles and len(candles) >= 20:
            tasks.append(ComputeTask(
                symbol=symbol,
                interval="1day",
                candles=candles
            ))
    
    if not tasks:
        logger.warning("No tasks to compute")
        return
    
    # Compute in parallel
    results = worker.compute_batch(tasks)
    
    # Write to cache
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
        
        # Categorize
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
    
    # Sort by change_pct
    momentum_data.sort(key=lambda x: abs(x.get('change_pct', 0)), reverse=True)
    breakout_data.sort(key=lambda x: abs(x.get('change_pct', 0)), reverse=True)
    
    # Cache aggregated results
    cache.set(CacheKeys.all_snapshots(), all_snapshots, TTLPolicy.SCANNER)
    cache.set(CacheKeys.momentum(), momentum_data, TTLPolicy.SCANNER)
    cache.set(CacheKeys.breakout(), breakout_data, TTLPolicy.SCANNER)
    cache.set(CacheKeys.reversal(), reversal_data, TTLPolicy.SCANNER)
    cache.set(CacheKeys.signals(), all_signals, TTLPolicy.SCANNER)
    
    elapsed = (time.time() - start) * 1000
    
    # Update worker status in cache
    cache.set("qai:worker:status", {
        'last_scan': datetime.now().isoformat(),
        'symbol_count': len(results),
        'elapsed_ms': round(elapsed, 0),
        'pid': os.getpid()
    }, TTLPolicy.SCANNER * 2)
    
    logger.info(f"Scan cycle: {len(results)} symbols in {elapsed:.0f}ms")


def main():
    """Main entry point."""
    global _running
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 60)
    logger.info("HP Scanner Worker Process Starting")
    logger.info(f"PID: {os.getpid()}")
    logger.info("=" * 60)
    
    # Start indicator worker pool
    start_indicator_workers()
    worker = get_indicator_worker()
    logger.info(f"Worker pool started with {worker.num_workers} processes")
    
    # Load symbols
    symbols = load_symbols()
    if not symbols:
        logger.error("No symbols loaded, exiting")
        return
    
    # Load candles once (they update slowly for daily)
    candles_map = load_candles(symbols)
    
    # Initial cache warm
    logger.info("Running initial cache warm-up...")
    run_scan_cycle(symbols, candles_map)
    
    # Main loop
    scan_interval = 5  # seconds
    scan_count = 0
    
    logger.info(f"Starting scan loop (interval: {scan_interval}s)")
    
    while _running:
        try:
            scan_count += 1
            run_scan_cycle(symbols, candles_map)
            
            # Every 60 cycles (5 minutes), reload candles
            if scan_count % 60 == 0:
                logger.info("Refreshing candle data...")
                candles_map = load_candles(symbols)
            
        except Exception as e:
            logger.error(f"Scan cycle error: {e}")
        
        # Sleep until next cycle
        time.sleep(scan_interval)
    
    # Cleanup
    logger.info("Shutting down worker pool...")
    worker.stop()
    logger.info("HP Scanner Worker Process stopped")


if __name__ == "__main__":
    main()
