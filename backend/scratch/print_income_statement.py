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
        inc = await client._make_request("GET", f"/fundamentals/{isin}/income-statement")
        print("Status:", inc.get("status"))
        if inc.get("data"):
            print("History items:")
            for h in inc["data"].get("history", []):
                print(h)
            print("\nFull statement particulars:")
            for item in inc["data"].get("full_statement", []):
                particular = item.get("particular")
                history_vals = [f"{v['period']}: {v['value']}" for v in item.get("history", [])]
                print(f"- {particular} -> {history_vals[:2]}")
    except Exception as e:
        print("Error:", e)
        
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(test())
