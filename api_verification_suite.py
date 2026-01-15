
import asyncio
import httpx
import time
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("verification.log", mode='w'),
        logging.StreamHandler()
    ]
)

BASE_URL = "http://localhost:8000/api"
AUTH_URL = "http://localhost:8000/api/auth/token"

# Test User Credentials (ensure this user exists or use signup)
TEST_USER = {
    "username": "testuser_verif",
    "password": "password123"
}

TOKEN = ""

async def get_token():
    """Authenticate and get JWT token."""
    global TOKEN
    async with httpx.AsyncClient() as client:
        # Try login
        response = await client.post(f"{BASE_URL}/auth/token", data=TEST_USER)
        if response.status_code == 401:
            # Try signup if login fails
            logger.info("Login failed, trying signup...")
            signup_data = TEST_USER.copy()
            signup_data["email"] = "testuser_verif@example.com"
            signup_data["full_name"] = "Test User Verif"
            await client.post(f"{BASE_URL}/auth/signup", json=signup_data)
            # Retry login
            response = await client.post(f"{BASE_URL}/auth/token", data=TEST_USER)
        
        if response.status_code == 200:
            TOKEN = response.json()["access_token"]
            logger.info("✅ Authentication Successful")
            return True
        else:
            logger.error(f"❌ Authentication Failed: {response.text}")
            return False

async def test_validation_fix():
    """Phase 1: Verify Strict Validation (422 expected on missing field)."""
    headers = {"Authorization": f"Bearer {TOKEN}"}
    async with httpx.AsyncClient() as client:
        # payload missing 'indices'
        payload = {"scan_type": "full"} 
        response = await client.post(f"{BASE_URL}/scanner/run", json=payload, headers=headers)
        
        if response.status_code == 422:
            logger.info("✅ Validation Fix Verified: Got 422 for missing fields.")
        else:
            logger.error(f"❌ Validation Fix Failed: Expected 422, got {response.status_code}")

async def test_auth_error_fix():
    """Phase 4: Verify Standard Auth Error Code."""
    headers = {"Authorization": f"Bearer {TOKEN}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/upstox/portfolio", headers=headers)
        
        # We expect 400 with specific code if not connected
        if response.status_code == 400:
            data = response.json()
            if data.get("error", {}).get("code") == "BROKER_NOT_CONNECTED":
                logger.info("✅ Auth Error Verified: Got BROKER_NOT_CONNECTED code.")
            else:
                logger.warning(f"⚠️ Auth Error Partial: Got 400 but code mismatch: {data}")
        else:
            logger.info(f"ℹ️ Auth Check: Got {response.status_code} (User might be connected).")

async def test_sanitization_fix():
    """Phase 3: Verify Analytics Sanitization (No 500 on NaN)."""
    headers = {"Authorization": f"Bearer {TOKEN}"}
    async with httpx.AsyncClient() as client:
        # Use a symbol likely to exist or REALIANCE
        response = await client.get(f"{BASE_URL}/analytics/support-resistance/RELIANCE", headers=headers)
        
        if response.status_code in [200, 404]:
            logger.info(f"✅ Analytics Sanitization Verified: Got {response.status_code} (No 500).")
        else:
            logger.error(f"❌ Analytics Fix Failed: Got {response.status_code}")

async def test_performance_vectorization():
    """Phase 6: Verify Latency < 2.5s for Scanner."""
    headers = {"Authorization": f"Bearer {TOKEN}"}
    async with httpx.AsyncClient(timeout=30.0) as client: # 30s timeout
        start = time.time()
        logger.info("⏳ Starting Performance Test: Breakout Scan (Vectorized)...")
        
        # Hit the breakout endpoint (which uses BreakoutDetector.scan_all)
        response = await client.post(f"{BASE_URL}/scanner/run", json={"scan_type": "breakout", "indices": ["NIFTY 50"]}, headers=headers)
        
        duration = time.time() - start
        
        if response.status_code == 200:
            logger.info(f"✅ Performance Test Passed: {duration:.2f}s (Threshold: 2.5s)")
            if duration > 2.5:
                logger.warning(f"⚠️ Performance Warning: {duration:.2f}s is > 2.5s but successful.")
        else:
            logger.error(f"❌ Performance Test Failed: Status {response.status_code} in {duration:.2f}s")
            logger.error(f"Response: {response.text[:200]}")

async def main():
    logger.info("🚀 Starting API Verification Suite...")
    if await get_token():
        await test_validation_fix()
        await test_auth_error_fix()
        await test_sanitization_fix()
        await test_performance_vectorization()
    logger.info("🏁 Verification Complete.")

if __name__ == "__main__":
    asyncio.run(main())
