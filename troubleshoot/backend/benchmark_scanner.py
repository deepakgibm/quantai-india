import asyncio
import time
import logging
import os
# Force localhost for DB connection for local benchmark
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:admin@localhost:5432/quantai"

from services.hp_scanner_service import get_hp_scanner_service
from services.dragonfly_client import get_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Benchmark")

async def benchmark_scanner():
    print("Starting HP Scanner Benchmark...")
    service = get_hp_scanner_service()
    
    # Warm up symbols
    await service._load_symbols()
    print(f"Loaded {len(service._symbols)} symbols.")
    
    # Measure one cycle
    start = time.perf_counter()
    print("Running one scan cycle...")
    await service._run_scan_cycle_async()
    duration = (time.perf_counter() - start) * 1000
    
    print(f"\n========================================")
    print(f"BENCHMARK RESULT")
    print(f"Scan Cycle Time: {duration:.2f}ms")
    print(f"========================================\n")
    
    # Check cache
    cache = get_cache()
    await cache.set_async("benchmark_test", True)
    if cache.is_available():
        stats = cache.get_stats()
        print(f"Cache Stats: {stats}")
    else:
        print("Cache unavailable for verification.")

if __name__ == "__main__":
    asyncio.run(benchmark_scanner())
