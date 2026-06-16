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
        actions = await client._make_request("GET", f"/fundamentals/{isin}/corporate-actions")
        print("Status:", actions.get("status"))
        if actions.get("data"):
            print("Keys:", list(actions["data"].keys()) if isinstance(actions["data"], dict) else "Data is list")
            print("Data sample:")
            data = actions["data"]
            if isinstance(data, list):
                for item in data[:5]:
                    print(item)
            elif isinstance(data, dict):
                for k, v in list(data.items())[:3]:
                    print(f"{k}: {v[:2] if isinstance(v, list) else v}")
    except Exception as e:
        print("Error:", e)
        
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(test())
