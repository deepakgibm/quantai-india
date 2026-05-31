import asyncio
import sys
from pathlib import Path
import json
import requests

sys.path.append(str(Path(__file__).parent.parent))
from services.upstox_client import get_upstox_client

async def main():
    client = get_upstox_client()
    url = "https://api.upstox.com/v2/option/chain"
    
    # BANKNIFTY instrument key is NSE_INDEX|Nifty Bank
    params = {
        "instrument_key": "NSE_INDEX|Nifty Bank",
        "expiry_date": "2026-06-25"
    }
    
    print(f"Calling BANKNIFTY Option Chain for expiry: {params['expiry_date']}")
    r = requests.get(url, headers=client.headers, params=params)
    print(f"Status Code: {r.status_code}")
    if r.status_code == 200:
        data = r.json().get("data", [])
        print(f"Data length: {len(data)}")
        if data:
            print("Success! Sample strike price:", data[0].get("strike_price"))
    else:
        print("Error:", r.text)

if __name__ == "__main__":
    asyncio.run(main())
