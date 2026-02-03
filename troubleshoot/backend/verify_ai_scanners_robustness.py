import asyncio
import aiohttp
import json
import time
from typing import Dict, Any

BASE_URL = "http://127.0.0.1:8000/api"
AUTH_URL = f"{BASE_URL}/auth/login"
SCANNER_ENDPOINTS = [
    "/ai/trend-finder",
    "/ai/breakout-detector",
    "/ai/top5-picks",
    "/ai/momentum",
    "/ai/mean-reversion",
    "/ai/gap",
    "/ai/vwap",
    "/ai/sr-bounce"
]

TEST_USER = {
    "email": "dthat53@gmail.com",
    "password": "admin1243"
}

async def get_token(session):
    async with session.post(AUTH_URL, json=TEST_USER) as resp:
        if resp.status == 200:
            data = await resp.json()
            return data.get("access_token")
        else:
            text = await resp.text()
            print(f"Auth failed: {resp.status} - Body: {text}")
            return None

async def test_endpoint(session, token, endpoint):
    url = f"{BASE_URL}{endpoint}"
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Testing {url}...")
    start = time.time()
    try:
        async with session.get(url, headers=headers, timeout=60) as resp:
            elapsed = (time.time() - start) * 1000
            if resp.status != 200:
                print(f"  [FAIL] Status {resp.status} in {elapsed:.1f}ms")
                try:
                    print(f"  Body: {await resp.text()}")
                except: pass
                return False
            
            data = await resp.json()
            status = data.get("status")
            debug = data.get("debug", {})
            stocks_len = len(data.get("stocks", []))
            
            # Validation
            required_keys = ["status", "count", "stocks", "scan_type", "description", "debug"]
            missing = [k for k in required_keys if k not in data]
            
            if missing:
                print(f"  [FAIL] Missing keys: {missing}")
                return False
            
            print(f"  [PASS] {status} in {elapsed:.1f}ms. Stocks: {stocks_len}")
            print(f"  Telemetry: Expected={debug.get('symbols_expected')}, Scanned={debug.get('symbols_scanned')}, Missing={debug.get('symbols_missing')}, Failed={debug.get('symbols_failed')}")
            print(f"  Stats: Buy={debug.get('buy_signals')}, Sell={debug.get('sell_signals')}")
            print(f"  Source: {debug.get('price_source')}, Timeframe: {debug.get('indicator_timeframe') or debug.get('indicators_timeframe')}")
            
            if status == "no_signal":
                print(f"  Reason: {data.get('message')}")
            
            return True
    except Exception as e:
        print(f"  [ERROR] {endpoint}: {str(e)}")
        return False

async def main():
    async with aiohttp.ClientSession() as session:
        token = await get_token(session)
        if not token:
            return
        
        results = []
        for ep in SCANNER_ENDPOINTS:
            res = await test_endpoint(session, token, ep)
            results.append(res)
            print("-" * 40)
        
        success_count = sum(1 for r in results if r)
        print(f"\nSummary: {success_count}/{len(SCANNER_ENDPOINTS)} endpoints passed.")

if __name__ == "__main__":
    asyncio.run(main())
