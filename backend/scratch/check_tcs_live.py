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

async def main():
    client = get_upstox_client()
    symbol = "TCS"
    # TCS key is NSE_EQ|INE467B01029
    inst_key = "NSE_EQ|INE467B01029"
    # Next near expiry is 2026-05-28
    expiry = "2026-05-28"
    
    print("====================================================")
    print(f"Checking live Upstox API response for symbol: {symbol}")
    print(f"Instrument Key: {inst_key}")
    print(f"Expiry Date: {expiry}")
    print("====================================================")
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {client.access_token}"
    }
    if hasattr(client, 'api_key'):
        headers["Api-Key"] = client.api_key
    elif os.getenv("UPSTOX_API_KEY"):
        headers["Api-Key"] = os.getenv("UPSTOX_API_KEY")
        
    # Check authorization / token validity details
    token_part = client.access_token[:15] + "..." if client.access_token else "None"
    print(f"Using Token: {token_part}")
    print(f"Headers: {json.dumps({k: (v[:15] + '...' if k == 'Authorization' else v) for k, v in headers.items()})}")
    
    url = "https://api.upstox.com/v2/option/chain"
    params = {
        "instrument_key": inst_key,
        "expiry_date": expiry
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"\n--- Raw API Response Details ---")
        print(f"API HTTP Status Code: {response.status_code}")
        print(f"Response Reason: {response.reason}")
        print(f"Is Empty/Null response? {response.text.strip() == '' or response.text.strip() == 'null'}")
        print(f"Raw Response Body (truncated): {response.text[:2000]}")
        
        try:
            payload = response.json()
            status = payload.get("status")
            data = payload.get("data")
            errors = payload.get("errors")
            
            print(f"\n--- Parsed Payload Structure ---")
            print(f"Payload Status: {status}")
            print(f"Errors returned: {errors}")
            if data is not None:
                print(f"Is Data a list? {isinstance(data, list)}")
                if isinstance(data, list):
                    print(f"Data length: {len(data)}")
                    if len(data) > 0:
                        print("Data contains elements. Option chain data exists.")
                    else:
                        print("Data is empty []. Market-hours restrictions are causing empty response.")
            else:
                print("Data is Null/None.")
        except json.JSONDecodeError:
            print("Response is not JSON.")
            
    except Exception as e:
        print(f"Request execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
