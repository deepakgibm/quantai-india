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
    
    # Query NIFTY 50 for June 25, 2026
    params = {
        "instrument_key": "NSE_INDEX|Nifty 50",
        "expiry_date": "2026-06-25"
    }
    
    print(f"Calling NIFTY 50 Option Chain for expiry: {params['expiry_date']}")
    r = requests.get(url, headers=client.headers, params=params)
    if r.status_code == 200:
        res = r.json()
        data = res.get("data", [])
        print(f"Data length: {len(data)}")
        
        # Print details of a few strikes closer to ATM (23000, 24000)
        target_strikes = [23000.0, 24000.0]
        for strike in data:
            if strike.get("strike_price") in target_strikes:
                print(f"\n================ Strike Price: {strike.get('strike_price')} ================")
                print(json.dumps(strike, indent=2))
    else:
        print(f"Error: {r.status_code} - {r.text}")

if __name__ == "__main__":
    asyncio.run(main())
