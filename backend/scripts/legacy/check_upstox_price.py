import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.live_price_enricher import fetch_live_ltp
from config import settings

async def check():
    symbol = "MANAPPURAM"
    token = settings.UPSTOX_ACCESS_TOKEN
    print(f"Fetching live LTP for {symbol} from Upstox...")
    prices = await fetch_live_ltp([symbol], token)
    print(f"UPSTOX_RESULT: {prices}")

if __name__ == "__main__":
    asyncio.run(check())
