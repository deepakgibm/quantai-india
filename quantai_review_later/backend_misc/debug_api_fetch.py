
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to sys.path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from backend.services.upstox_client import get_upstox_client

async def test_fetch():
    client = get_upstox_client()
    
    # Test with ABB
    symbol = "ABB"
    instrument_key = "NSE_EQ|INE117A01022"
    
    print(f"Testing fetch for {symbol} ({instrument_key})...")
    
    from_dt = datetime(2023, 1, 1)
    to_dt = datetime(2024, 1, 1)
    
    try:
        df = await client.get_historical_data(
            symbol=symbol,
            instrument_key=instrument_key,
            from_date=from_dt,
            to_date=to_dt,
            interval="1minute"
        )
        
        print(f"Result: {len(df)} records")
        if not df.empty:
            print(df.head())
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_fetch())
