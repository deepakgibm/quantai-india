import asyncio
import aiohttp
import sys

BASE_URL = "http://127.0.0.1:8000"

# Mock user credentials (assuming login works)
TEST_USER = {
    "email": "dthat53@gmail.com",
    "password": "admin1243"
}

async def test_forecast():
    async with aiohttp.ClientSession() as session:
        # Login
        async with session.post(f"{BASE_URL}/api/auth/login", json=TEST_USER) as resp:
            if resp.status != 200:
                print(f"Login failed: {resp.status}")
                return
            data = await resp.json()
            token = data["access_token"]

        headers = {"Authorization": f"Bearer {token}"}
        
        # Test Predict
        url = f"{BASE_URL}/api/forecast/predict?symbol=ABB&timeframe=1d&horizon=5"
        print(f"Testing {url}...")
        
        async with session.get(url, headers=headers) as resp:
            print(f"Status: {resp.status}")
            txt = await resp.text()
            print(f"Response: {txt[:200]}...")

if __name__ == "__main__":
    asyncio.run(test_forecast())
