
import asyncio
import httpx
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("HeatmapTest")

BASE_URL = "http://localhost:8000/api"

# Reuse the credentials from verification suite
TEST_USER = {
    "username": "testuser_verif",
    "password": "password123"
}

async def get_token():
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/auth/token", data=TEST_USER)
        if response.status_code == 200:
            token = response.json()["access_token"]
            logger.info("✅ Auth Token Acquired")
            return token
        else:
            logger.error(f"❌ Auth Failed: {response.text}")
            return None

async def test_heatmap_sectors():
    token = await get_token()
    if not token:
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Check Health first
        try:
            health = await client.get(f"{BASE_URL.replace('/api', '')}/")
            logger.info(f"🏥 Root Status: {health.status_code}")
        except Exception as e:
            logger.error(f"❌ Server Down? {e}")
            return

        logger.info(f"📡 Requesting: GET {BASE_URL}/heatmap/sectors")
        response = await client.get(f"{BASE_URL}/heatmap/sectors", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Status 200 OK")
            
            # Check structure
            status = data.get("status")
            sectors = data.get("data", [])
            
            logger.info(f"Response Status: {status}")
            logger.info(f"Sectors Count: {len(sectors)}")
            
            if sectors:
                logger.info(f"First Sector Preview: {json.dumps(sectors[0], indent=2)}")
            else:
                logger.warning("⚠️ Sectors list is empty. (Cache might be cold)")
                logger.info("You may need to run the Heatmap Worker or use /api/heatmap/seed to populate data.")
                
        else:
            logger.error(f"❌ Request Failed: {response.status_code}")
            logger.error(response.text)

if __name__ == "__main__":
    asyncio.run(test_heatmap_sectors())
