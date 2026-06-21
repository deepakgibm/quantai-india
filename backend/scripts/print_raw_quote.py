import asyncio
import sys
import os
import json

sys.path.append(os.path.abspath("backend"))

from dotenv import load_dotenv
load_dotenv("backend/.env")

from services.upstox_client import get_upstox_client
from services.live_price_enricher import get_instrument_key

async def main():
    client = get_upstox_client()
    # Query for RELIANCE
    instrument_key = get_instrument_key("RELIANCE")
    
    # We make the raw request directly using _make_request to see the exact response format
    params = {"instrument_key": instrument_key}
    raw_data = await client._make_request("GET", "/market-quote/quotes", params=params)
    print(json.dumps(raw_data, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
