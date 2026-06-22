import asyncio
import sys
from pathlib import Path

# Add backend directory to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from services.upstox_client import get_upstox_client

async def main():
    client = get_upstox_client()
    instrument_key = "NSE_EQ|INE002A01018" # RELIANCE
    expiry_date = "2026-05-28"
    
    print("Testing option chain request...")
    params = {
        "instrument_key": instrument_key,
        "expiry_date": expiry_date
    }
    
    try:
        res = await client._make_request("GET", "/option/chain", params=params)
        print("Response Success!")
        print(f"Status: {res.get('status')}")
        print(f"Data type: {type(res.get('data'))}")
        if res.get('data'):
            print(f"Data length: {len(res.get('data'))}")
            print(f"First element: {res.get('data')[0]}")
        else:
            print(f"Data is empty or None: {res.get('data')}")
            print(f"Full response: {res}")
    except Exception as e:
        print(f"Failed: {type(e).__name__} - {e}")
        
if __name__ == "__main__":
    asyncio.run(main())
