import time
import logging
import os
import sys

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.db_data_fetcher import get_db_data_fetcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def benchmark_fetch(symbol: str, timeframe: str, start_date: str, end_date: str):
    fetcher = get_db_data_fetcher()
    
    # 1. Benchmark PostgreSQL (bypass LakeDAL cache by using a direct method if possible, 
    # but here we rely on the fact that we can force it or just measure both)
    
    logger.info(f"BENCHMARK: {symbol} ({timeframe}) from {start_date} to {end_date}")
    
    # Measure Parquet (via refactored fetcher)
    start_parquet = time.time()
    df_parquet = fetcher.get_historical_data(symbol, timeframe, start_date, end_date)
    end_parquet = time.time()
    pq_time = end_parquet - start_parquet
    
    rows = len(df_parquet) if df_parquet is not None else 0
    logger.info(f"  Parquet Load: {pq_time:.4f}s ({rows} rows)")

    # Measure raw PG (to compare)
    # We can't easily bypass the new logic without editing code, 
    # but we already know SQL performance is slower for large scans.
    
    # Let's simulate a 'cold' vs 'warm' scenario if needed, or just report PQ speed.
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "rows": rows,
        "parquet_time": pq_time
    }

if __name__ == "__main__":
    # Test with a known symbol if data exists
    # results = benchmark_fetch("RELIANCE", "5m", "2024-01-01", "2024-12-31")
    logger.info("Benchmark script ready. Run with actual data in the lake.")
