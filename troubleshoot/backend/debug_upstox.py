import os
import aiohttp
import asyncio
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
BASE_URL = "https://api.upstox.com/v2"

async def test_upstox():
    print(f"Token length: {len(ACCESS_TOKEN) if ACCESS_TOKEN else 0}")
    if not ACCESS_TOKEN:
        print("No token found!")
        return

    tests = [
        {"param": "instrument_key", "value": "NSE_INDEX|Nifty 50"},
        {"param": "instrument_key", "value": "NSE_EQ|ABB"},
        {"param": "symbol", "value": "ABB"},
        {"param": "symbol", "value": "NSE_EQ|ABB"},
    ]
    
    url = f"{BASE_URL}/market-quote/ltp"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Accept": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        for t in tests:
            print(f"\nFetching param {t['param']}={t['value']}...")
            params = {t['param']: t['value']}
            async with session.get(url, headers=headers, params=params) as resp:
                print(f"Status: {resp.status}")
                txt = await resp.text()
                print(f"Response: {txt[:200]}")

if __name__ == "__main__":
    asyncio.run(test_upstox())
