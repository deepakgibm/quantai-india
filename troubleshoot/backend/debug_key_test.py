
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
UPSTOX_BASE_URL = "https://api.upstox.com/v2"

async def test_key(symbol, key):
    url = f"{UPSTOX_BASE_URL}/market-quote/ltp"
    headers = {
        "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}",
        "Accept": "application/json"
    }
    params = {"instrument_key": key}
    print(f"Testing {symbol}: {key} ...")
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            print(f"Status: {resp.status}")
            txt = await resp.text()
            print(f"Response: {txt}")

async def main():
    # Test keys from DB
    await test_key("MEDANTA", "NSE_EQ|INE474Q01031")
    await test_key("AMBER", "NSE_EQ|INE371P01015")
    await test_key("ANGELONE", "NSE_EQ|INE732I01013")
    await test_key("GRSE", "NSE_EQ|INE382Z01011")

if __name__ == "__main__":
    asyncio.run(main())
