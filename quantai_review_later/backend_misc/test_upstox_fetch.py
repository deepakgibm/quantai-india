
import asyncio
import sys
from pathlib import Path
from datetime import datetime
import urllib.parse

# Add project root to sys.path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from backend.services.upstox_client import get_upstox_client
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from services.upstox_client import get_upstox_client

async def test_fetch():
    client = get_upstox_client()
    
    # RELIANCE key
    reliance_key = "NSE_EQ|INE002A01018"
    # ABB key
    abb_key = "NSE_EQ|INE117A01022"
    
    from_dt = datetime(2022, 1, 1)
    to_dt = datetime(2022, 3, 1)
    
    print("Testing RELIANCE (raw key)...")
    try:
        df = await client.get_historical_data("RELIANCE", reliance_key, from_dt, to_dt)
        print(f"Success: {len(df)} records")
    except Exception as e:
        print(f"Failed: {e}")
        
    print("\nTesting RELIANCE (encoded key)...")
    try:
        df = await client.get_historical_data("RELIANCE", urllib.parse.quote(reliance_key), from_dt, to_dt)
        print(f"Success: {len(df)} records")
    except Exception as e:
        print(f"Failed: {e}")

    print("\nTesting ABB (raw key)...")
    try:
        df = await client.get_historical_data("ABB", abb_key, from_dt, to_dt)
        print(f"Success: {len(df)} records")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_fetch())
