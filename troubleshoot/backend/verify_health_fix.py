
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()
BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN") # Just borrowing a token for auth if needed

async def main():
    async with aiohttp.ClientSession() as session:
        # 1. Check Health (Should be 200 OK)
        print(f"Checking {BASE_URL}/api/health/ ...")
        async with session.get(f"{BASE_URL}/api/health/") as resp:
            print(f"Health Status: {resp.status}")
            txt = await resp.text()
            print(f"Health Body: {txt[:100]}...") # Truncate

        # 2. Check Orchestrator Status (Needs Auth)
        # We need a valid user token. Usually test suite gets one or uses mock.
        # UPSTOX_ACCESS_TOKEN is for Upstox, not the App.
        # Let's try to login or assume we can hit it without auth if we didn't protect it
        # Wait, I added `Depends(get_current_user)` to `get_orchestrator_status` in `market_data.py`?
        # Yes: current_user: User = Depends(get_current_user)
        # So we need a token.
        
        # Login first
        login_url = f"{BASE_URL}/api/auth/login"
        creds = {"email": "dthat53@gmail.com", "password": "admin1243"}
        
        print(f"Logging in...")
        token = None
        async with session.post(login_url, json=creds) as resp:
            if resp.status == 200:
                data = await resp.json()
                token = data.get("access_token")
                print("Login successful")
            else:
                 print(f"Login failed: {resp.status}")
        
        if token:
            headers = {"Authorization": f"Bearer {token}"}
            print(f"Checking {BASE_URL}/api/market/orchestrator-status ...")
            async with session.get(f"{BASE_URL}/api/market/orchestrator-status", headers=headers) as resp:
                print(f"Orch Status Code: {resp.status}")
                if resp.status == 200:
                    print(await resp.json())
                else:
                    print(await resp.text())
        else:
            print("Skipping Orchestrator check due to auth failure")

if __name__ == "__main__":
    asyncio.run(main())
