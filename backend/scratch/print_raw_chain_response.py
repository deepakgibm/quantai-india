import asyncio
import sys
from pathlib import Path
import requests

sys.path.append(str(Path(__file__).parent.parent))
from services.upstox_client import get_upstox_client

async def main():
    client = get_upstox_client()
    url = "https://api.upstox.com/v2/option/chain"
    
    # 1. Query RELIANCE for June 25, 2026
    params_rel = {
        "instrument_key": "NSE_EQ|INE002A01018",
        "expiry_date": "2026-06-25"
    }
    print(f"Calling RELIANCE Option Chain for expiry: {params_rel['expiry_date']}")
    r_rel = requests.get(url, headers=client.headers, params=params_rel)
    print(f"Status Code: {r_rel.status_code}")
    print(f"Raw Response: {r_rel.text[:2000]}")
    
    # 2. Query NIFTY 50 for June 4, 2026
    params_nif = {
        "instrument_key": "NSE_INDEX|Nifty 50",
        "expiry_date": "2026-06-04"
    }
    print(f"\nCalling NIFTY 50 Option Chain for expiry: {params_nif['expiry_date']}")
    r_nif = requests.get(url, headers=client.headers, params=params_nif)
    print(f"Status Code: {r_nif.status_code}")
    print(f"Raw Response: {r_nif.text[:2000]}")

if __name__ == "__main__":
    asyncio.run(main())
