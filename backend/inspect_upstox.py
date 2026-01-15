import httpx
import json
from config import settings

async def inspect_upstox_quote():
    access_token = settings.UPSTOX_ACCESS_TOKEN
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    url = "https://api.upstox.com/v2/market-quote/quotes"
    params = {"instrument_key": "NSE_EQ|INE002A01018"} # RELIANCE
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Error: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    import asyncio
    asyncio.run(inspect_upstox_quote())
