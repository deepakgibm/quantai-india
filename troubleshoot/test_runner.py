
import asyncio
import httpx
import logging
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler("test_runner.log", mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TestRunner")

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api"
TOKEN = None

# Credentials
TEST_USER = {
    "username": "testuser_verif",
    "password": "password123"
}

async def get_token(client):
    global TOKEN
    if TOKEN:
        return TOKEN
    
    # Try login first
    logger.info("🔐 Attempting Login...")
    try:
        response = await client.post(f"{API_URL}/auth/token", data=TEST_USER)
        
        if response.status_code == 200:
            TOKEN = response.json().get("access_token")
            logger.info("✅ Login Successful")
            return TOKEN
        elif response.status_code == 401:
            logger.info("⚠️ Login Failed (401), attempting Signup...")
            # Try signup
            signup_data = TEST_USER.copy()
            signup_data["email"] = "testuser_verif@example.com"
            signup_data["full_name"] = "Test User Verif"
            
            signup_res = await client.post(f"{API_URL}/auth/signup", json=signup_data)
            if signup_res.status_code in [200, 201]:
                logger.info("✅ Signup Successful, retrying Login...")
            elif signup_res.status_code == 400 and "already exists" in signup_res.text.lower():
                logger.info("ℹ️ User already exists (Signup skipped), retrying Login...")
            else:
                logger.error(f"❌ Signup Failed: {signup_res.status_code} - {signup_res.text}")
                # Don't return yet, try login one last time just in case
            
            # Retry Login
            response = await client.post(f"{API_URL}/auth/token", data=TEST_USER)
            if response.status_code == 200:
                TOKEN = response.json().get("access_token")
                logger.info("✅ Login Successful (Retry)")
                return TOKEN
            else:
                logger.error(f"❌ Login Retry Failed: {response.status_code} - {response.text}")
                return None
        else:
             logger.error(f"❌ Initial Login Error: {response.status_code} - {response.text}")
             return None

    except Exception as e:
        logger.error(f"❌ Auth Exception: {e}")
        return None

async def run_test(client, method, endpoint, name, payload=None, expected_status=[200], auth=False):
    """Generic test execution function."""
    url = f"{BASE_URL}{endpoint}" if endpoint.startswith("/") else f"{API_URL}/{endpoint}"
    headers = {}
    
    if auth:
        token = await get_token(client)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        else:
            logger.warning(f"⚠️ Skipping {name} (Auth failed)")
            return False

    try:
        if method == "GET":
            response = await client.get(url, headers=headers)
        elif method == "POST":
            response = await client.post(url, json=payload, headers=headers)
        elif method == "PUT":
            response = await client.put(url, json=payload, headers=headers)
        elif method == "DELETE":
            response = await client.delete(url, headers=headers)
            
        if response.status_code in expected_status:
            logger.info(f"✅ {name}: {response.status_code}")
            return True
        else:
            logger.error(f"❌ {name}: Failed with {response.status_code}")
            logger.error(f"   Response: {response.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"❌ {name}: Exception {e}")
        return False

async def test_core(client):
    logger.info("--- Testing Core Infrastructure ---")
    await run_test(client, "GET", "/", "Root")
    await run_test(client, "GET", "/health", "Health")
    await run_test(client, "GET", "/ready", "Readiness")
    await run_test(client, "GET", "/api/auth/me", "Get Me", auth=True)
    await run_test(client, "GET", "/api/settings/", "Get Settings", auth=True)
    await run_test(client, "GET", "/api/risk/", "Get Risk Settings", auth=True)

async def test_market(client):
    logger.info("--- Testing Market Data ---")
    await run_test(client, "GET", "/api/market/health", "Market Health")
    await run_test(client, "GET", "/api/market/nifty100/status", "NIFTY 100 Status")
    # Using 'RELIANCE' as the test stock
    await run_test(client, "GET", "/api/market/nifty100/top-movers", "Top Movers")
    await run_test(client, "GET", "/api/market/heatmap", "Sector Heatmap", auth=True)
    await run_test(client, "GET", "/api/trading/market-indices", "Market Indices")
    await run_test(client, "GET", "/api/trading/instruments", "Instruments")

async def test_scanners(client):
    logger.info("--- Testing Scanners ---")
    await run_test(client, "GET", "/api/scanner/strategies", "Scanner Strategies", auth=True)
    await run_test(client, "GET", "/api/scanner/indices", "Scanner Indices", auth=True)
    await run_test(client, "GET", "/api/scanner/presets", "Scanner Presets", auth=True)
    # Test V2/V3 APIs
    await run_test(client, "GET", "/api/v2/scanner/status", "V2 Scanner Status")
    await run_test(client, "GET", "/api/v3/scanner/status", "V3 Scanner Status")
    await run_test(client, "GET", "/api/ai/momentum-scanner", "AI Momentum Scanner", auth=True)

async def test_trading_ai(client):
    logger.info("--- Testing AI & Trading ---")
    await run_test(client, "GET", "/api/ai/strategies", "AI Strategies", auth=True)
    await run_test(client, "GET", "/api/ai/market-analysis", "Market Analysis", auth=True)
    await run_test(client, "GET", "/api/orders/", "Get Orders", auth=True)
    await run_test(client, "GET", "/api/trading/stats", "Dashboard Stats", auth=True)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", type=str, default="all", help="Module to test: core, market, scanners, trading")
    args = parser.parse_args()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Pre-auth
        await get_token(client)
        
        if args.module in ["all", "core"]:
            await test_core(client)
        if args.module in ["all", "market"]:
            await test_market(client)
        if args.module in ["all", "scanners"]:
            await test_scanners(client)
        if args.module in ["all", "trading"]:
            await test_trading_ai(client)

if __name__ == "__main__":
    asyncio.run(main())
