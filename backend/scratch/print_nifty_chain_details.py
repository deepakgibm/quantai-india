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
    print(f"Status Code: {r.status_code}")
    
    if r.status_code == 200:
        res = r.json()
        data = res.get("data", [])
        print(f"Data length: {len(data)}")
        if len(data) > 0:
            print("\nFirst strike details:")
            print(json.dumps(data[0], indent=2))
            
            # Print list of all strike prices
            strikes = [item.get("strike_price") for item in data]
            print(f"\nAll strike prices in response: {strikes}")
            
            # Print unique expiries in the options objects (if they are listed there)
            c_exp = data[0].get("call_options", {}).get("expiry")
            p_exp = data[0].get("put_options", {}).get("expiry")
            print(f"Call Option Expiry: {c_exp}")
            print(f"Put Option Expiry: {p_exp}")
            
            # Check market data fields inside call_options
            c_market_data = data[0].get("call_options", {}).get("market_data", {})
            print(f"\nMarket data fields in call option: {list(c_market_data.keys())}")
            print(json.dumps(c_market_data, indent=2))
    else:
        print(f"Error Response: {r.text}")

if __name__ == "__main__":
    asyncio.run(main())
