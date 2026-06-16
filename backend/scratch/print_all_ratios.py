import asyncio
import sys
import os

# Add parent directory of scratch to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.upstox_client import get_upstox_client

async def test():
    client = get_upstox_client()
    isin = "INE002A01018" # Reliance
    
    try:
        ratios = await client._make_request("GET", f"/fundamentals/{isin}/key-ratios")
        print("Status:", ratios.get("status"))
        if ratios.get("data"):
            for item in ratios["data"]:
                print(f"Name: {item.get('name')} | Company: {item.get('company_value')} | Sector: {item.get('sector_value')}")
    except Exception as e:
        print("Error:", e)
        
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(test())
