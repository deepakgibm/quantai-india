import asyncio
import sys
import os
import urllib.parse

# Add parent directory of scratch to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.upstox_client import get_upstox_client

async def test():
    client = get_upstox_client()
    isin = "INE002A01018"
    inst_key = f"NSE_EQ|{isin}"
    
    print("Testing Upstox Competitors API with Instrument Key in Path...")
    try:
        encoded_key = urllib.parse.quote(inst_key, safe='')
        comp = await client._make_request("GET", f"/fundamentals/{encoded_key}/competitors")
        print("Competitors Response Status:", comp.get("status"))
        print("Competitors Response Data sample:", comp.get("data")[:3] if comp.get("data") else None)
    except Exception as e:
        print("Competitors API failed:", e)

    print("\nTesting Upstox News API with instrument_keys (plural)...")
    try:
        # News requires instrument_keys (plural)
        news = await client._make_request("GET", f"/news?category=instrument_keys&instrument_keys={inst_key}")
        print("News Response Status:", news.get("status"))
        print("News Response Data sample length:", len(news.get("data", [])) if news.get("data") else 0)
        print("News data sample:", news.get("data")[:2] if news.get("data") else None)
    except Exception as e:
        print("News API failed:", e)

    await client.aclose()

if __name__ == "__main__":
    asyncio.run(test())
