import asyncio
import sys
from pathlib import Path
import json
import requests

# Add backend directory to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from services.upstox_client import get_upstox_client

async def test_symbol(symbol: str, inst_key: str, expiry: str):
    client = get_upstox_client()
    print(f"\n====================================================")
    print(f"Testing Symbol: {symbol} (key: {inst_key}, expiry: {expiry})")
    print(f"====================================================")
    
    params = {
        "instrument_key": inst_key,
        "expiry_date": expiry
    }
    
    full_url = "https://api.upstox.com/v2/option/chain"
    try:
        response = requests.get(full_url, headers=client.headers, params=params)
        print(f"API HTTP Status Code: {response.status_code}")
        
        if response.status_code == 200:
            payload = response.json()
            status = payload.get("status")
            data = payload.get("data")
            
            print(f"Payload Status: {status}")
            if data:
                print(f"Number of strikes returned: {len(data)}")
                # Inspect the first strike in detail
                print("\n--- Detailed Structure of a single strike ---")
                sample_strike = data[0]
                print(json.dumps(sample_strike, indent=2))
            else:
                print("Data is empty or None")
        else:
            print(f"Error Response: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

async def main():
    # RELIANCE next monthly expiry: June 25, 2026
    await test_symbol("RELIANCE", "NSE_EQ|INE002A01018", "2026-06-25")
    
    # NIFTY next weekly expiry: June 04, 2026
    await test_symbol("NIFTY 50", "NSE_INDEX|Nifty 50", "2026-06-04")

if __name__ == "__main__":
    asyncio.run(main())
