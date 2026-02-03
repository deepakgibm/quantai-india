import asyncio
import aiohttp
import os
from datetime import datetime
from typing import Optional, Dict, Tuple
from dotenv import load_dotenv

load_dotenv()

UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
UPSTOX_BASE_URL = "https://api.upstox.com/v2"

class UpstoxVerifier:
    """Verifies stock prices against Upstox REST API."""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.cache: Dict[str, Tuple[float, datetime]] = {}
        self.cache_ttl_seconds = 60  # Cache prices for 60 seconds
    
    async def get_price(self, session: aiohttp.ClientSession, symbol: str) -> Optional[float]:
        """Fetch current price from Upstox REST API."""
        if not self.access_token:
            print("No token")
            return None
        
        try:
            url = f"{UPSTOX_BASE_URL}/market-quote/ltp"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            }
            # The App uses 'symbol' param, not 'instrument_key'.
            params = {"symbol": symbol}
            
            print(f"Fetching symbol={symbol}...")
            async with session.get(url, headers=headers, params=params, timeout=5) as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    print(f"Data: {str(data)[:200]}...")
                    if data.get("status") == "success" and "data" in data:
                        # Data keys might vary (e.g. NSE_EQ:ABB), so grab the first valid price found
                        ltp_data = data["data"]
                        for key, val in ltp_data.items():
                            price = val.get("last_price")
                            if price:
                                print(f"Found price: {price}")
                                return float(price)
        except Exception as e:
            print(f"[UPSTOX] Error fetching {symbol}: {e}")
        
        print("Returning None")
        return None

async def main():
    verifier = UpstoxVerifier(UPSTOX_ACCESS_TOKEN)
    async with aiohttp.ClientSession() as session:
        await verifier.get_price(session, "ABB")
        await verifier.get_price(session, "INDIA VIX")

if __name__ == "__main__":
    asyncio.run(main())
