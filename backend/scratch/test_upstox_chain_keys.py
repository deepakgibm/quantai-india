import asyncio
import sys
from pathlib import Path
import requests

sys.path.append(str(Path(__file__).parent.parent))
from services.upstox_client import get_upstox_client

async def test_key_expiry(key: str, expiry: str, client):
    url = "https://api.upstox.com/v2/option/chain"
    params = {
        "instrument_key": key,
        "expiry_date": expiry
    }
    print(f"Testing Key: {key} | Expiry: {expiry}")
    try:
        r = requests.get(url, headers=client.headers, params=params)
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json().get("data", [])
            print(f"  Data length: {len(data)}")
            if len(data) > 0:
                print(f"  SUCCESS! Sample strike: {data[0].get('strike_price')}")
                return True
        else:
            print(f"  Response: {r.text}")
    except Exception as e:
        print(f"  Failed: {e}")
    return False

async def main():
    client = get_upstox_client()
    
    # Try different key formats for RELIANCE
    reliance_keys = [
        "NSE_EQ|INE002A01018",
        "NSE_EQ|RELIANCE",
        "NSE_EQ:RELIANCE",
    ]
    
    # Try different key formats for NIFTY 50
    nifty_keys = [
        "NSE_INDEX|Nifty 50",
        "NSE_INDEX|NIFTY 50",
        "NSE_INDEX|NIFTY_50",
        "NSE_INDEX:Nifty 50",
        "NSE_INDEX:Nifty50",
    ]
    
    # Try expiries
    expiries = ["2026-06-25", "2026-06-04"]
    
    print("--- Testing RELIANCE ---")
    for key in reliance_keys:
        for exp in expiries:
            success = await test_key_expiry(key, exp, client)
            if success:
                break
                
    print("\n--- Testing NIFTY 50 ---")
    for key in nifty_keys:
        for exp in expiries:
            success = await test_key_expiry(key, exp, client)
            if success:
                break

if __name__ == "__main__":
    asyncio.run(main())
