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
        bs = await client._make_request("GET", f"/fundamentals/{isin}/balance-sheet?fs=true")
        print("Status:", bs.get("status"))
        if bs.get("data"):
            # Print the structure of a history item
            print("History items:")
            for h in bs["data"].get("history", []):
                print(h)
                
            # Print the particulars in full statement
            print("\nFull statement particulars:")
            for item in bs["data"].get("full_statement", []):
                particular = item.get("particular")
                history_vals = [f"{v['period']}: {v['value']}" for v in item.get("history", [])]
                print(f"- {particular} -> {history_vals[:2]}")
    except Exception as e:
        print("Error:", e)
        
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(test())
