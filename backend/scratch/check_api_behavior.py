import asyncio
import os
import sys
from pathlib import Path
import json
import requests

# Add backend directory to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from services.upstox_client import get_upstox_client

async def test_symbol(symbol: str, inst_key: str, expiry: str = None):
    client = get_upstox_client()
    print(f"\n--- Testing Symbol: {symbol} (key: {inst_key}, expiry: {expiry}) ---")
    
    params = {"instrument_key": inst_key}
    if expiry:
        params["expiry_date"] = expiry
        
    full_url = "https://api.upstox.com/v2/option/chain"
    try:
        response = requests.get(full_url, headers=client.headers, params=params)
        
        print(f"API HTTP Status Code: {response.status_code}")
        print(f"Is Empty/Null response? {response.text.strip() == '' or response.text.strip() == 'null'}")
        
        try:
            payload = response.json()
            status = payload.get("status")
            data = payload.get("data")
            errors = payload.get("errors")
            
            print(f"Payload Status: {status}")
            print(f"Errors returned: {errors}")
            if data is not None:
                print(f"Data is list? {isinstance(data, list)}")
                if isinstance(data, list):
                    print(f"Data length: {len(data)}")
                    if len(data) > 0:
                        print(f"First element key elements: {list(data[0].keys())}")
                        # Print sample elements to see if they are empty
                        c_opt = data[0].get("call_options")
                        p_opt = data[0].get("put_options")
                        print(f"Call option present: {c_opt is not None}, Put option present: {p_opt is not None}")
                        if c_opt:
                            print(f"Call option sample market data: {c_opt.get('market_data')}")
                    else:
                        print("Data list is empty []")
            else:
                print("Data is Null/None")
        except json.JSONDecodeError:
            print(f"Response is not JSON. Response body: {response.text[:200]}")
            
    except Exception as e:
        print(f"Request failed: {e}")

async def main():
    # RELIANCE
    await test_symbol("RELIANCE", "NSE_EQ|INE002A01018", "2026-05-28")
    await test_symbol("RELIANCE", "NSE_EQ|INE002A01018", None)
    
    # NIFTY
    await test_symbol("NIFTY", "NSE_INDEX|Nifty 50", "2026-05-28")
    await test_symbol("NIFTY", "NSE_INDEX|Nifty 50", None)

if __name__ == "__main__":
    asyncio.run(main())
