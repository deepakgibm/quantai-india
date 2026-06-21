import asyncio
import sys
import os

sys.path.append(os.path.abspath("backend"))

from dotenv import load_dotenv
load_dotenv("backend/.env")

# Ensure DRAGONFLY_HOST is localhost on host machine
os.environ["DRAGONFLY_HOST"] = "localhost"

from services.upstox_client import get_upstox_client
from services.live_price_enricher import get_instrument_key

async def main():
    client = get_upstox_client()
    symbols = ["ADANIENSOL", "SPMLINFRA", "PANACHE", "RELIANCE", "TCS"]
    keys = []
    for s in symbols:
        k = get_instrument_key(s)
        print(f"{s} instrument key: {k}")
        if k:
            keys.append(k)
            
    print("\nCalling get_live_quotes...")
    quotes = await client.get_live_quotes(keys)
    print(f"Returned {len(quotes)} quotes:")
    for k, q in quotes.items():
        print(f"  {k}: last_price={q.get('last_price')}, previous_close={q.get('previous_close')}, change_percent={q.get('change_percent')}, volume={q.get('volume')}")

if __name__ == "__main__":
    asyncio.run(main())
