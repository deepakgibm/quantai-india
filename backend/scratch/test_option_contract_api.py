import asyncio
import sys
from pathlib import Path
import json
import requests

sys.path.append(str(Path(__file__).parent.parent))
from services.upstox_client import get_upstox_client

async def test_symbol(symbol_name, key):
    client = get_upstox_client()
    url = "https://api.upstox.com/v2/option/contract"
    params = {"instrument_key": key}
    print(f"\nCalling GET /option/contract for {symbol_name} ({key})")
    try:
        r = requests.get(url, headers=client.headers, params=params)
        print(f"Status Code: {r.status_code}")
        if r.status_code == 200:
            res = r.json()
            data = res.get("data", [])
            print(f"Data length: {len(data)}")
            if len(data) > 0:
                # Print unique expiries
                expiries = sorted(list(set(item.get("expiry") for item in data if item.get("expiry"))))
                print(f"Unique Expiries found: {expiries}")
                return expiries
        else:
            print(f"Response: {r.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    return []

async def main():
    await test_symbol("NIFTY 50", "NSE_INDEX|Nifty 50")
    await test_symbol("RELIANCE", "NSE_EQ|INE002A01018")
    await test_symbol("TCS", "NSE_EQ|INE467B01029")

if __name__ == "__main__":
    asyncio.run(main())
