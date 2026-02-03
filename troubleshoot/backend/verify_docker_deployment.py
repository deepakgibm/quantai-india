
import asyncio
import aiohttp
import sys

BACKEND_URL = "http://localhost:8000/api/health/"
FRONTEND_URL = "http://localhost:3000"

async def check_url(session, url, name):
    try:
        print(f"Checking {name} at {url}...")
        async with session.get(url) as resp:
            print(f"{name} Status: {resp.status}")
            if resp.status < 400:
                print(f"✅ {name} is UP")
                return True
            else:
                print(f"❌ {name} returned error status")
                text = await resp.text()
                print(f"Response: {text[:100]}")
                return False
    except Exception as e:
        print(f"❌ {name} unreachable: {e}")
        return False

async def main():
    async with aiohttp.ClientSession() as session:
        backend_ok = await check_url(session, BACKEND_URL, "Backend API")
        
        # Test specific fixed endpoints
        print("Checking Top Movers Alias (Should be Public)...")
        async with session.get("http://localhost:8000/api/market/nifty100/top-movers") as resp:
            print(f"Top Movers Status: {resp.status}")
            if resp.status == 200:
                print("✅ Top Movers is Public and Accessible")
            else:
                print(f"❌ Top Movers returned {resp.status}")
                backend_ok = False

        print("Checking Engine Performance (Should be 200/401)...")
        async with session.get("http://localhost:8000/api/engines/performance") as resp:
            print(f"Engine Perf Status: {resp.status}")
            if resp.status == 404:
                 print("❌ Engine Perf returned 404 (Prefix/Path Issues)")
                 backend_ok = False
            else:
                 print(f"✅ Engine Perf Route Exists (Status: {resp.status})")
        
        # Test AI endpoints (Expect 401 without auth, but that proves route exists vs 404)
        print("Checking AI Trend Finder (Expect 401)...")
        async with session.get("http://localhost:8000/api/ai/trend-finder") as resp:
             print(f"AI Trend Finder Status: {resp.status}")
             if resp.status == 404:
                 print("❌ AI Trend Finder returned 404 (Still Missing)")
                 backend_ok = False
             else:
                 print("✅ AI Trend Finder Route Exists")

        frontend_ok = await check_url(session, FRONTEND_URL, "Frontend UI")
        
        if backend_ok and frontend_ok:
            print("\n🎉 Deployment Verified Successfully!")
            sys.exit(0)
        else:
            print("\n⚠️ Deployment Verification Failed")
            sys.exit(1)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
