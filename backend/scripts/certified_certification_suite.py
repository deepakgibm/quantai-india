import httpx
import asyncio
import logging

# Configuration targeting the internal Docker network if running inside, 
# or localhost if running from the development host.
BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("QuantAICertification")

class CertificationSuite:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=30.0, follow_redirects=True)
        self.token = None
        self.refresh_token = None
        self.headers = {}
        self.results = {
            "auth_basic": "PENDING",
            "auth_refresh": "PENDING",
            "market_data": "PENDING",
            "scanners": "PENDING",
            "screener": "PENDING",
            "websockets": "PENDING",
            "ai_features": "SKIPPED",
            "errors": []
        }

    async def run_all(self):
        logger.info("Starting Total Backend Certification Suite...")
        
        # 1. Health Check
        if not await self.test_health():
            logger.error("Health check failed. Aborting certification.")
            return self.results

        # 2. Auth Flow (Signup -> Login)
        await self.test_auth_flow()
        
        if not self.token:
            logger.error("Authentication failed. Cannot proceed with protected API tests.")
            return self.results

        # 3. Market Data & Indicators
        await self.test_market_data()

        # 4. Scanners (Standard & HP)
        await self.test_scanners()

        # 5. Institutional Screener
        await self.test_screener()

        # 6. WebSocket Connectivity
        await self.test_websockets()

        logger.info("Certification Suite completed.")
        self.print_report()
        return self.results

    async def test_health(self):
        try:
            resp = await self.client.get("/api/health/")
            if resp.status_code == 200:
                logger.info("✅ Health check passed")
                return True
            logger.error(f"❌ Health check returned {resp.status_code}")
            return False
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return False

    async def test_auth_flow(self):
        logger.info("Testing Auth Flow & Refresh Rotation...")
        try:
            # Try login with default test credentials
            test_user = {
                "email": "test@quantai.in",
                "password": "testpassword123"
            }
            
            resp = await self.client.post("/api/auth/login", json=test_user)
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.headers = {"Authorization": f"Bearer {self.token}"}
                logger.info("✅ Auth Login successful with token pair")
                self.results["auth_basic"] = "PASSED"
                
                # Test Refresh Logic
                if self.refresh_token:
                    refresh_resp = await self.client.post("/api/auth/refresh", json={"refresh_token": self.refresh_token})
                    if refresh_resp.status_code == 200:
                        refresh_data = refresh_resp.json()
                        self.token = refresh_data.get("access_token")
                        self.headers = {"Authorization": f"Bearer {self.token}"}
                        logger.info("✅ Auth Refresh Token Rotation successful")
                        self.results["auth_refresh"] = "PASSED"
                    else:
                        logger.error(f"❌ Auth Refresh failed: {refresh_resp.status_code} - {refresh_resp.text}")
                        self.results["auth_refresh"] = "FAILED"
                else:
                    logger.error("❌ Login response missing refresh_token")
                    self.results["auth_refresh"] = "FAILED"
                    
            else:
                logger.warning(f"⚠️ Initial login failed (expected if DB empty): {resp.status_code}")
                # Try signup if login failed
                test_signup = {
                    "email": "test@quantai.in",
                    "username": "testuser",
                    "full_name": "Test User",
                    "password": "testpassword123"
                }
                resp = await self.client.post("/api/auth/signup", json=test_signup)
                if resp.status_code in [200, 201]:
                    logger.info("✅ Auth Signup successful")
                    # Try login again
                    resp = await self.client.post("/api/auth/login", json=test_user)
                    if resp.status_code == 200:
                        login_data = resp.json()
                        self.token = login_data.get("access_token")
                        self.refresh_token = login_data.get("refresh_token")
                        self.headers = {"Authorization": f"Bearer {self.token}"}
                        logger.info("✅ Auth Login (post-signup) successful")
                        self.results["auth_basic"] = "PASSED"
                        
                        # Test Refresh for new user
                        refresh_resp = await self.client.post("/api/auth/refresh", json={"refresh_token": self.refresh_token})
                        if refresh_resp.status_code == 200:
                            logger.info("✅ Auth Refresh successful for new user")
                            self.results["auth_refresh"] = "PASSED"
                        else:
                            self.results["auth_refresh"] = "FAILED"
                else:
                    logger.error(f"❌ Auth flow failed: {resp.text}")
                    self.results["auth_basic"] = "FAILED"
                    self.results["errors"].append(f"Auth: {resp.text}")
        except Exception as e:
            logger.error(f"❌ Auth Exception: {e}")
            self.results["auth_basic"] = f"CRASHED: {e}"

    async def test_market_data(self):
        logger.info("Testing Market Data APIs...")
        try:
            resp = await self.client.get("/api/market/indices", headers=self.headers)
            if resp.status_code == 200:
                logger.info("✅ Market Indices API passed")
                self.results["market_data"] = "PASSED"
            else:
                self.results["market_data"] = "FAILED"
                self.results["errors"].append(f"MarketData: {resp.status_code} - {resp.text}")
        except Exception as e:
            self.results["market_data"] = "ERROR"

    async def test_scanners(self):
        logger.info("Testing Scanners (Unified/HP)...")
        try:
            # Test HP Momentum (Quick)
            hp_resp = await self.client.get("/api/scanners/v3/momentum", headers=self.headers)
            if hp_resp.status_code == 200:
                logger.info("✅ HP Momentum API passed")
            
            # Test Standard Run
            scan_req = {
                "indices": ["NIFTY 50"],
                "timeframe": "15m",
                "strategies": ["trend_finder"]
            }
            run_resp = await self.client.post("/api/scanner/run", json=scan_req, headers=self.headers)
            if run_resp.status_code == 200:
                logger.info("✅ Standard Scanner Run passed")
                self.results["scanners"] = "PASSED"
            else:
                logger.error(f"❌ Scanner failed: {run_resp.text}")
                self.results["scanners"] = "FAILED"
                self.results["errors"].append(f"Scanners: {run_resp.text}")
        except Exception as e:
            logger.error(f"❌ Scanner Exception: {e}")
            self.results["scanners"] = f"ERROR: {e}"

    async def test_screener(self):
        logger.info("Testing Institutional Screener & Background Tasks...")
        try:
            resp = await self.client.get("/api/screener/status", headers=self.headers)
            if resp.status_code == 200:
                logger.info("✅ Screener Status API passed")
                
                # Test Rankings
                rank_resp = await self.client.get("/api/screener/rankings?limit=5", headers=self.headers)
                if rank_resp.status_code == 200:
                    logger.info("✅ Screener Rankings API passed")
                
                # Test Async Run
                run_resp = await self.client.post("/api/screener/run", headers=self.headers)
                if run_resp.status_code == 200:
                    run_data = run_resp.json()
                    if run_data.get("status") == "accepted" and "task_id" in run_data:
                        logger.info(f"✅ Screener Async Task triggered: {run_data.get('task_id')}")
                        self.results["screener"] = "PASSED"
                    else:
                        logger.error(f"❌ Screener run returned invalid format: {run_data}")
                        self.results["screener"] = "FAILED"
                else:
                    logger.error(f"❌ Screener run failed: {run_resp.status_code}")
                    self.results["screener"] = "FAILED"
            else:
                self.results["screener"] = "FAILED"
                self.results["errors"].append(f"Screener: {resp.text}")
        except Exception as e:
            self.results["screener"] = f"ERROR: {e}"

    async def test_websockets(self):
        logger.info("Testing WebSocket stability...")
        try:
            import websockets
            uri = f"{WS_URL}/api/ws/live"
            async with websockets.connect(uri) as ws:
                # Use 10s timeout to survive 5s heartbeat cycles
                msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                logger.info(f"✅ WebSocket connection successful, received: {msg[:50]}...")
                self.results["websockets"] = "PASSED"
        except Exception as e:
            logger.error(f"❌ WebSocket test failed: {type(e).__name__}: {e}")
            self.results["websockets"] = "FAILED"

    def print_report(self):
        print("\n" + "="*50)
        print("QUANT AI BACKEND CERTIFICATION REPORT")
        print("="*50)
        for key, val in self.results.items():
            if key == "errors": continue
            print(f"{key.replace('_', ' ').title():<20}: {val}")
        print("="*50)
        if self.results["errors"]:
            print("CRITICAL ERRORS FOUND:")
            for err in self.results["errors"][:5]:
                print(f"- {err}")
        print("="*50 + "\n")

if __name__ == "__main__":
    suite = CertificationSuite()
    asyncio.run(suite.run_all())
