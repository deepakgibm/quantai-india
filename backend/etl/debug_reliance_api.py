import asyncio
import os
import sys
from datetime import datetime, date
from pathlib import Path
import pandas as pd

# Add project root to path for imports
project_root = Path(__file__).resolve().parents[2]
backend_dir = project_root / 'backend'
sys.path.append(str(backend_dir))
sys.path.append(str(project_root))

from backend.services.instrument_resolver import resolve_instrument_id, get_instrument_info
from backend.services.upstox_client import get_upstox_client

async def debug_reliance_fetch():
    try:
        client = get_upstox_client()
        symbol = "RELIANCE"
        
        # Resolve
        inst_id = resolve_instrument_id(symbol, exchange='NSE')
        info = get_instrument_info(inst_id)
        instrument_key = info.instrument_key
        
        print(f"Instrument Key: {instrument_key}")
        
        # Fetch 1m data for today (Feb 9th)
        start_date = datetime(2026, 2, 8) # Sunday
        end_date = datetime(2026, 2, 10) # Tomorrow
        
        print(f"Fetching 1m data from {start_date} to {end_date}...")
        df_1m = await client.get_historical_data(symbol, instrument_key, start_date, end_date, "1minute")
        
        if df_1m.empty:
            print("Fetched dataframe is EMPTY.")
        else:
            print(f"Fetched {len(df_1m)} candles.")
            df_sorted = df_1m.sort_values('timestamp')
            print("\n--- First 5 Candles ---")
            print(df_sorted.head())
            print("\n--- Last 5 Candles ---")
            print(df_sorted.tail())
            
            # Check unique dates
            df_1m['date'] = df_1m['timestamp'].dt.date
            print("\n--- Dates Found ---")
            print(df_1m['date'].unique())
            
        await client.aclose()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_reliance_fetch())
