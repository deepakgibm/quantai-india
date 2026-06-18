"""
Standalone HP Scanner Worker Process — Celery distributed mode.
Runs independently from FastAPI to orchestrate scanning.

This process:
1. Loads symbols from database
2. Loads daily candles
3. Dispatches indicator calculation chunks to Celery workers
4. Collects results and writes aggregated data (reversal, momentum, breakout, etc.) to Dragonfly
5. Runs continuously in a loop
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
    """Load symbols from database using instrument_master."""
    import psycopg2
    from config import settings
    
    try:
        conn = psycopg2.connect(settings.SYNC_DATABASE_URL)
        cur = conn.cursor()
        # Use instrument_master as source of truth for active symbols
        cur.execute("""
            SELECT symbol FROM instrument_master 
            WHERE is_active = TRUE AND exchange = 'NSE' AND series = 'EQ'
            ORDER BY symbol
            LIMIT 200
        """)
        symbols = [row[0] for row in cur.fetchall()]
        conn.close()
        logger.info(f"Loaded {len(symbols)} symbols from instrument_master")
        return symbols
    except Exception as e:
        logger.error(f"Failed to load symbols: {e}")
        return []


def load_candles(symbols: List[str]) -> Dict[str, List[Dict]]:
    """Load candles for all symbols using batch query from stock_candle + instrument_master."""
    import psycopg2
    from config import settings
    
    candles_map = {}
    
    if not symbols:
        return candles_map
    
    try:
        conn = psycopg2.connect(settings.SYNC_DATABASE_URL)
        cur = conn.cursor()
        
        # Single batch query using new schema: stock_candle + instrument_master
        cur.execute("""
            SELECT im.symbol, sc.candle_ts, sc.open, sc.high, sc.low, sc.close, sc.volume
            FROM stock_candle sc
            JOIN instrument_master im ON sc.instrument_id = im.instrument_id
            WHERE im.symbol = ANY(%s) AND sc.timeframe = 1440
            ORDER BY im.symbol, sc.candle_ts DESC
        """, (symbols,))
        
        rows = cur.fetchall()
        conn.close()
        
        # Group rows by symbol
        from collections import defaultdict
        symbol_rows = defaultdict(list)
        for row in rows:
            symbol_rows[row[0]].append(row)
        
        # Process each symbol's rows
        for symbol, sym_rows in symbol_rows.items():
            recent_rows = sym_rows[:200]
            if len(recent_rows) >= 1:
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
        
        logger.info(f"Loaded candles for {len(candles_map)} symbols using stock_candle")
        return candles_map
        
    except Exception as e:
        logger.error(f"Failed to load candles: {e}")
        return {}


def run_scan_cycle(symbols: List[str], candles_map: Dict[str, List[Dict]]):
    """Execute one scan cycle by distributing to Celery tasks."""
    start = time.time()
    
    # Chunk symbols into batches of 40 symbols
    chunk_size = 40
    chunks = []
    
    current_chunk = []
    for symbol in symbols:
        candles = candles_map.get(symbol)
        if candles and len(candles) >= 1:
            current_chunk.append({
                "symbol": symbol,
                "interval": "1day",
                "candles": candles
            })
            if len(current_chunk) >= chunk_size:
                chunks.append(current_chunk)
                current_chunk = []
    if current_chunk:
        chunks.append(current_chunk)
        
    if not chunks:
        logger.warning("No tasks to compute")
        return
        
    # Dispatch to Celery group
    from celery import group
    from tasks.hp_scanner_tasks import compute_chunk_task
    
    try:
        job = group(compute_chunk_task.s(chunk) for chunk in chunks)
        result_group = job.apply_async()
        
        # Wait for all chunks to finish (Map step)
        results_list_of_lists = result_group.get(timeout=15)
    except Exception as e:
        logger.error(f"Celery parallel execution failed: {e}")
        return

    # Flatten results (Reduce step)
    results = [res for sublist in results_list_of_lists for res in sublist]
    
    # Aggregate results and write to cache (on this orchestrator node)
    cache = get_cache()
    all_snapshots = []
    momentum_data = []
    breakout_data = []
    reversal_data = []
    all_signals = []
    
    for res in results:
        snapshot = res.get("snapshot")
        symbol = res.get("symbol")
        if not snapshot:
            continue
            
        all_snapshots.append(snapshot)
        
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
    
    logger.info(f"Scan cycle: {len(results)} symbols in {elapsed:.0f}ms (distributed via Celery)")


def main():
    """Main entry point."""
    global _running
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 60)
    logger.info("HP Scanner Worker Process Starting (Celery mode)")
    logger.info(f"PID: {os.getpid()}")
    logger.info("=" * 60)
    
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
    
    logger.info("HP Scanner Worker Process stopped")


if __name__ == "__main__":
    main()
