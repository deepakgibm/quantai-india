import asyncio
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).resolve().parents[2]
backend_dir = project_root / 'backend'
sys.path.append(str(backend_dir))
sys.path.append(str(project_root))

from backend.services.upstox_client import get_upstox_client
from backend.services.instrument_resolver import resolve_instrument_id, get_instrument_info

async def debug_api():
    symbol = 'RELIANCE'
    instrument_id = resolve_instrument_id(symbol, exchange='NSE')
    info = get_instrument_info(instrument_id)
    
    print(f"DEBUG: {symbol}")
    print(f"  Instrument ID: {instrument_id}")
    print(f"  Instrument Key: {info.instrument_key if info else 'NONE'}")
    
    if not info: return

    client = get_upstox_client()
    
    # Try fetching Daily for the missing range
    from_date = datetime(2026, 1, 25)
    to_date = datetime.now()
    
    print(f"  Fetching 1d: {from_date.date()} to {to_date.date()}")
    df = await client.get_historical_data(symbol, info.instrument_key, from_date, to_date, "day")
    
    if df.empty:
        print("  !!! Daily Data EMPTY")
    else:
        print(f"  ✓ Fetched {len(df)} daily candles")
        print(df.tail())

    # Try fetching 1m
    print(f"  Fetching 1m: {from_date} to {to_date}")
    df_1m = await client.get_historical_data(symbol, info.instrument_key, from_date, to_date, "1minute")
    if df_1m.empty:
        print("  !!! 1m Data EMPTY")
    else:
        print(f"  ✓ Fetched {len(df_1m)} 1m candles")
        print(df_1m.tail())

    await client.aclose()

if __name__ == "__main__":
    asyncio.run(debug_api())
