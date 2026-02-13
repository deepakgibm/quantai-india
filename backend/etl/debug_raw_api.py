import asyncio
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).resolve().parents[2]
backend_dir = project_root / 'backend'
sys.path.append(str(backend_dir))
sys.path.append(str(project_root))

from backend.services.upstox_client import get_upstox_client
from backend.services.instrument_resolver import resolve_instrument_id, get_instrument_info

async def raw_debug():
    symbol = 'RELIANCE'
    instrument_id = resolve_instrument_id(symbol, exchange='NSE')
    info = get_instrument_info(instrument_id)
    
    client = get_upstox_client()
    
    # Range covering this week
    from_date = datetime(2026, 2, 1)
    to_date = datetime.now()
    
    print(f"FETCHING RELIANCE {from_date.date()} to {to_date.date()} (1d)")
    
    # Raw request logic from upstox_client.py
    import urllib.parse
    encoded_key = urllib.parse.quote(info.instrument_key, safe='')
    endpoint = f"/historical-candle/{encoded_key}/day/{to_date.strftime('%Y-%m-%d')}/{from_date.strftime('%Y-%m-%d')}"
    
    data = await client._make_request("GET", endpoint)
    
    print("\nRAW DATA STATUS:", data.get("status"))
    if data.get("data") and data["data"].get("candles"):
        candles = data["data"]["candles"]
        print(f"TOTAL CANDLES RETURNED: {len(candles)}")
        for c in candles[:10]:
             print(f"  {c[0]}: {c[4]}") # Timestamp and Close
    else:
        print("  !!! NO CANDLES IN RESPONSE DATA")

    await client.aclose()

if __name__ == "__main__":
    asyncio.run(raw_debug())
