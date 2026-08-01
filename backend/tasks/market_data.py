from celery_app import celery_app
from services.upstox_client import get_upstox_client
from database import AsyncSessionLocal
from datetime import datetime, timedelta
import asyncio
import json
import os
from core.duckdb_engine import engine as duckdb_engine

@celery_app.task
def fetch_1min_candles():
    asyncio.run(_fetch_candles_async("1minute"))

@celery_app.task
def fetch_5min_candles():
    asyncio.run(_fetch_candles_async("5minute"))

async def _fetch_candles_async(interval: str):
    client = get_upstox_client()
    
    # Load symbols
    json_file = "nifty200_instruments.json"
    if not os.path.exists(json_file):
        print("Nifty 200 JSON not found")
        return
        
    with open(json_file, "r") as f:
        symbols = json.load(f)
        
    # Fetch recent data
    from_dt = datetime.now() - timedelta(days=1) 
    to_dt = datetime.now()
    
    # Configurable symbol limit with rate-limiting delay for larger lists
    limit_str = os.getenv("CANDLE_FETCH_LIMIT", "")
    limit = int(limit_str) if limit_str.isdigit() else None
    target_symbols = symbols[:limit] if limit is not None else symbols
    
    async with AsyncSessionLocal() as session:
        for sym, key in target_symbols:
            try:
                df = await client.get_historical_data(sym, key, from_dt, to_dt, interval)
                if not df.empty:
                    print(f"Fetched {len(df)} candles for {sym} ({interval})")
                    # Push historical table straight to Parquet datalake!
                    duckdb_engine.save_to_parquet(sym, interval, df)
                # Apply rate limiting delay when fetching bulk data
                if len(target_symbols) > 20:
                    await asyncio.sleep(0.3)
            except Exception as e:
                print(f"Error fetching {sym}: {e}")
