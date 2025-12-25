from celery_app import celery_app
from services.upstox_client import get_upstox_client
from database import AsyncSessionLocal
from models_alpha import StockData
from datetime import datetime, timedelta
import asyncio
import json
import os

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
    
    async with AsyncSessionLocal() as session:
        # Limit to first 20 for demo to respect rate limits
        for sym, key in symbols[:20]:
            try:
                df = await client.get_historical_data(sym, key, from_dt, to_dt, interval)
                if not df.empty:
                    print(f"Fetched {len(df)} candles for {sym} ({interval})")
                    # TODO: Upsert to DB
            except Exception as e:
                print(f"Error fetching {sym}: {e}")
