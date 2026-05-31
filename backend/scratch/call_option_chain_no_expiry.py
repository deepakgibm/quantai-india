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
    
    # 1. Test RELIANCE underlying key
    params = {"instrument_key": "NSE_EQ|INE002A01018"}
    print(f"Calling /option/chain with underlying key: {params['instrument_key']}")
    r = requests.get(url, headers=client.headers, params=params)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text[:1000]}")
    
    # 2. Test NIFTY 50 index key
    params = {"instrument_key": "NSE_INDEX|Nifty 50"}
    print(f"\nCalling /option/chain with underlying key: {params['instrument_key']}")
    r = requests.get(url, headers=client.headers, params=params)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text[:1000]}")

if __name__ == "__main__":
    asyncio.run(main())
