import asyncio
import sys
from pathlib import Path
import json
import requests

sys.path.append(str(Path(__file__).parent.parent))
from services.upstox_client import get_upstox_client

async def test_endpoint(path: str, params: dict, client):
    url = f"https://api.upstox.com/v2{path}"
    print(f"Testing endpoint: {path}")
    try:
        r = requests.get(url, headers=client.headers, params=params)
        print(f"  Status Code: {r.status_code}")
        print(f"  Body (truncated): {r.text[:500]}")
    except Exception as e:
        print(f"  Request failed: {e}")

async def main():
    client = get_upstox_client()
    params = {"instrument_key": "NSE_EQ|INE002A01018"}
    
    endpoints = [
        "/option/chain/expiry",
        "/option/chain/expiries",
        "/option/contract/expiry",
        "/option/expiry",
        "/option/expiries",
        "/option/dates",
        "/option/chain/dates",
        "/market-quote/quotes" # just to confirm connectivity
    ]
    
    for path in endpoints:
        await test_endpoint(path, params, client)

if __name__ == "__main__":
    asyncio.run(main())
