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
    
    # 1. Query RELIANCE for June 30, 2026
    params_rel = {
        "instrument_key": "NSE_EQ|INE002A01018",
        "expiry_date": "2026-06-30"
    }
    print(f"Calling RELIANCE Option Chain for expiry: {params_rel['expiry_date']}")
    r_rel = requests.get(url, headers=client.headers, params=params_rel)
    print(f"Status Code: {r_rel.status_code}")
    if r_rel.status_code == 200:
        data = r_rel.json().get("data", [])
        print(f"Data length: {len(data)}")
        if len(data) > 0:
            print("First strike info:")
            print(json.dumps(data[0], indent=2))
    else:
        print(f"Error: {r_rel.text}")

if __name__ == "__main__":
    asyncio.run(main())
