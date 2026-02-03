
import asyncio
import logging
import sys
import json
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_dir))

# Configure logging
logging.basicConfig(level=logging.INFO)

from services.dragonfly_client import get_cache, CacheKeys

async def verify_cache():
    cache = get_cache()
    
    print("\n--- Checking Momentum Cache ---")
    momentum = cache.get(CacheKeys.momentum())
    if momentum:
        print(f"SUCCESS: Momentum data found. {len(momentum)} items.")
        print(f"Sample: {momentum[0]['symbol']} {momentum[0]['change_pct']}%")
    else:
        print("WARNING: Momentum cache is EMPTY.")

    print("\n--- Checking Breakout Cache ---")
    breakout = cache.get(CacheKeys.breakout())
    if breakout:
        print(f"SUCCESS: Breakout data found. {len(breakout)} items.")
        print(f"Sample: {breakout[0]['symbol']} Type: {breakout[0]['breakout_type']}")
    else:
        print("WARNING: Breakout cache is EMPTY (Expected if history backfill is incomplete).")

if __name__ == "__main__":
    asyncio.run(verify_cache())
