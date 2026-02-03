#!/usr/bin/env python3
"""
Comprehensive QA Test Suite for QuantAI API
============================================
Tests all API endpoints with:
- Request/response validation
- Latency measurement (avg, P95)
- Stock price authenticity verification against Upstox REST API
- Failure classification

Author: QA Automation Engineer
Date: 2026-01-12
"""

import asyncio
import aiohttp
import json
import time
import statistics
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================
BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN", "")
UPSTOX_BASE_URL = "https://api.upstox.com/v2"

# Test user credentials
TEST_USER = {
    "email": "dthat53@gmail.com",
    "username": "dthat53",
    "full_name": "QA Tester",
    "password": "admin1243"
}

# Price deviation threshold (0.5%)
PRICE_DEVIATION_THRESHOLD = 0.005

# Latency thresholds
TARGET_LATENCY_MS = 2000
P95_FLAG_LATENCY_MS = 3000


# ============================================================
# ENUMS & DATA CLASSES
# ============================================================
class FailureCategory(Enum):
    NONE = "NONE"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTH_ERROR = "AUTH_ERROR"
    ROUTING_ERROR = "ROUTING_ERROR"
    UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
    AI_PROVIDER_LATENCY = "AI_PROVIDER_LATENCY"
    MARKET_DATA_UNAVAILABLE = "MARKET_DATA_UNAVAILABLE"
    PRICE_MISMATCH_UPSTOX = "PRICE_MISMATCH_UPSTOX"
    INTERNAL_EXCEPTION = "INTERNAL_EXCEPTION"
    STALE_DATA = "STALE_DATA"
    MOCK_OR_FAKE_DATA = "MOCK_OR_FAKE_DATA"


class PriceVerdict(Enum):
    VERIFIED_REAL_PRICE = "VERIFIED_REAL_PRICE"
    STALE_DATA = "STALE_DATA"
    MOCK_OR_FAKE_DATA = "MOCK_OR_FAKE_DATA"
    DATA_SOURCE_MISMATCH = "DATA_SOURCE_MISMATCH"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UPSTOX_UNAVAILABLE = "UPSTOX_UNAVAILABLE"


@dataclass
class PriceVerification:
    symbol: str
    app_price: float
    upstox_price: Optional[float]
    deviation_pct: Optional[float]
    verdict: PriceVerdict
    timestamp: str = ""


@dataclass
class EndpointResult:
    endpoint: str
    method: str
    status_code: int
    latency_ms: float
    success: bool
    failure_category: FailureCategory = FailureCategory.NONE
    error_message: str = ""
    price_verifications: List[PriceVerification] = field(default_factory=list)
    response_keys: List[str] = field(default_factory=list)
    recommended_fix: str = ""


@dataclass
class TestReport:
    run_timestamp: str
    total_endpoints: int
    passed: int
    failed: int
    avg_latency_ms: float
    p95_latency_ms: float
    endpoints_over_target: int
    price_verifications_total: int
    price_verifications_passed: int
    results: List[EndpointResult] = field(default_factory=list)


# ============================================================
# ENDPOINT DEFINITIONS
# ============================================================
# Endpoints that return stock price data (require Upstox verification)
PRICE_ENDPOINTS = [
    "/api/trading/top-gainers",
    "/api/trading/gainers-losers",
    "/api/market/nifty100/top-movers",
    "/api/market/top-movers",
    "/api/market/top-movers",
    "/api/scanner/ai/momentum",
    "/api/scanner/ai/vwap",
    "/api/scanner/hp/momentum",
    "/api/scanner/hp/breakout",
    "/api/scanner/hp/reversal",
    "/api/scanner/hp/trendfinder",
]

# All API endpoints to test
ENDPOINTS = [
    # System/Health
    {"path": "/", "method": "GET", "auth": False, "category": "System"},
    {"path": "/api/health/", "method": "GET", "auth": False, "category": "System"},
    {"path": "/api/health/ready", "method": "GET", "auth": False, "category": "System"},
    
    # Authentication (no auth required for signup/login)
    {"path": "/api/auth/signup", "method": "POST", "auth": False, "category": "Auth", "body": TEST_USER},
    {"path": "/api/auth/login", "method": "POST", "auth": False, "category": "Auth", "body": {"email": TEST_USER["email"], "password": TEST_USER["password"]}},
    {"path": "/api/auth/me", "method": "GET", "auth": True, "category": "Auth"},
    
    # Upstox
    {"path": "/api/upstox/status", "method": "GET", "auth": False, "category": "Upstox"},
    {"path": "/api/upstox/auth-url", "method": "GET", "auth": True, "category": "Upstox"},
    {"path": "/api/upstox/user-profile", "method": "GET", "auth": True, "category": "Upstox"},
    {"path": "/api/upstox/portfolio", "method": "GET", "auth": True, "category": "Upstox"},
    {"path": "/api/upstox/positions", "method": "GET", "auth": True, "category": "Upstox"},
    {"path": "/api/upstox/market-quote/ABB", "method": "GET", "auth": True, "category": "Upstox"},
    
    # Trading
    {"path": "/api/trading/health", "method": "GET", "auth": False, "category": "Trading"},
    {"path": "/api/trading/market-indices", "method": "GET", "auth": False, "category": "Trading"},
    {"path": "/api/trading/instruments", "method": "GET", "auth": False, "category": "Trading"},
    {"path": "/api/trading/stats", "method": "GET", "auth": True, "category": "Trading"},
    {"path": "/api/trading/dashboard", "method": "GET", "auth": True, "category": "Trading"},
    {"path": "/api/trading/top-gainers", "method": "GET", "auth": True, "category": "Trading"},
    {"path": "/api/trading/gainers-losers", "method": "GET", "auth": True, "category": "Trading"},
    
    # Heatmap (Now under Market)
    {"path": "/api/market/heatmap", "method": "GET", "auth": True, "category": "Heatmap"},
    {"path": "/api/market/sector/IT", "method": "GET", "auth": True, "category": "Heatmap"},
    
    # AI Scanners (Unified under /api/scanner/ai)
    {"path": "/api/ai/strategies", "method": "GET", "auth": True, "category": "AI"},
    {"path": "/api/ai/market-analysis", "method": "GET", "auth": True, "category": "AI"},
    {"path": "/api/ai/sentiment", "method": "GET", "auth": True, "category": "AI", "params": {"symbol": "ABB"}},
    {"path": "/api/ai/prompt", "method": "POST", "auth": True, "category": "AI", "body": {"prompt": "What are the top momentum stocks today?"}},

    # Orders
    {"path": "/api/orders/", "method": "GET", "auth": True, "category": "Orders"},
    
    # Risk & Settings
    {"path": "/api/risk/", "method": "GET", "auth": True, "category": "Risk"},
    
    # ML Forecast
    {"path": "/api/forecast/algorithms", "method": "GET", "auth": True, "category": "ML"},
    {"path": "/api/forecast/predict", "method": "GET", "auth": True, "category": "ML", "params": {"symbol": "ABB", "timeframe": "1d", "horizon": 5}},
    
    # Scanner (Unified)
    {"path": "/api/scanner/strategies", "method": "GET", "auth": True, "category": "Scanner"},
    {"path": "/api/scanner/presets", "method": "GET", "auth": True, "category": "Scanner"},
    
    # High-Performance Scanners
    {"path": "/api/scanner/hp/momentum", "method": "GET", "auth": True, "category": "HPScanner"},
    {"path": "/api/scanner/hp/breakout", "method": "GET", "auth": True, "category": "HPScanner"},
    
    # AI Scanners
    {"path": "/api/scanner/ai/momentum", "method": "GET", "auth": True, "category": "AIScanner"},
    {"path": "/api/scanner/ai/vwap", "method": "GET", "auth": True, "category": "AIScanner"},
    
    # Market
    {"path": "/api/market/top-movers", "method": "GET", "auth": False, "category": "Market"},
    {"path": "/api/market/status", "method": "GET", "auth": False, "category": "Market"},
    {"path": "/api/market/heatmap", "method": "GET", "auth": True, "category": "Market"},
    {"path": "/api/market/sector/IT", "method": "GET", "auth": True, "category": "Market"},
    
    # Analytics
    {"path": "/api/analytics/overview", "method": "GET", "auth": True, "category": "Analytics"},
    {"path": "/api/analytics/momentum/top", "method": "GET", "auth": True, "category": "Analytics"},
    {"path": "/api/analytics/volatility/ABB", "method": "GET", "auth": True, "category": "Analytics"},
    {"path": "/api/analytics/support-resistance/ABB", "method": "GET", "auth": True, "category": "Analytics"},
    {"path": "/api/analytics/archive/list", "method": "GET", "auth": True, "category": "Analytics"},
    {"path": "/api/analytics/archive/stats", "method": "GET", "auth": True, "category": "Analytics"},
    {"path": "/api/analytics/indicators/latest/ABB", "method": "GET", "auth": True, "category": "Analytics"},
]


# ============================================================
# UPSTOX PRICE VERIFICATION
# ============================================================
class UpstoxVerifier:
    """Verifies stock prices against Upstox REST API."""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.cache: Dict[str, Tuple[float, datetime]] = {}
        self.cache_ttl_seconds = 60
        self.instrument_map: Dict[str, str] = {}
        self.load_instruments()
    
    async def get_price(self, session: aiohttp.ClientSession, symbol: str) -> Optional[float]:
        """Fetch current price from Upstox REST API."""
        if not self.access_token:
            return None
        
        # Check cache
        if symbol in self.cache:
            price, cached_at = self.cache[symbol]
            if (datetime.now() - cached_at).seconds < self.cache_ttl_seconds:
                return price
        
        # Determine correct parameter based on known map
        params = {}
        if symbol in self.instrument_map:
            params = {"instrument_key": self.instrument_map[symbol]}
        else:
             # Fallback to symbol param (mostly for indices or unmapped)
             params = {"symbol": symbol}
             if "Nifty" in symbol or "VIX" in symbol:
                 # Indices might need specific key check or skip
                 # The map should hopefully cover Nifty 50 if populated
                 pass

        try:
            url = f"{UPSTOX_BASE_URL}/market-quote/ltp"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            }
            
            async with session.get(url, headers=headers, params=params, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("status") == "success" and "data" in data:
                        # Data keys might vary (e.g. NSE_EQ:ABB), so grab the first valid price found
                        ltp_data = data["data"]
                        for key, val in ltp_data.items():
                            price = val.get("last_price")
                            if price:
                                self.cache[symbol] = (float(price), datetime.now())
                                return float(price)
        except Exception as e:
            # print(f"[UPSTOX] Error fetching {symbol}: {e}") # Reduce noise
            pass
        
        return None

    def load_instruments(self):
        """Load instrument keys from JSON file."""
        try:
            # Look for nifty200_instruments.json in backend dir (../backend relative to this script)
            # Script is in troubleshoot/backend/, so we need ../../backend?
            # Or assume standard relative path.
            # troubleshoot/backend is 2 levels deep from root.
            # backend is 1 level deep from root.
            repo_root = Path(__file__).resolve().parent.parent.parent
            json_path = repo_root / "backend" / "nifty200_instruments.json"
            
            if json_path.exists():
                import json
                with open(json_path, 'r') as f:
                    data = json.load(f)
                    # data is list of [symbol, key] pairs
                    for item in data:
                        if len(item) >= 2:
                            self.instrument_map[item[0]] = item[1]
                print(f"Loaded {len(self.instrument_map)} instruments for verification.")
            else:
                print(f"Warning: Instrument map not found at {json_path}")
        except Exception as e:
            print(f"Error loading instruments: {e}")

    async def verify_price(
        self, 
        session: aiohttp.ClientSession, 
        symbol: str, 
        app_price: float
    ) -> PriceVerification:
        """Verify app price against Upstox price."""
        upstox_price = await self.get_price(session, symbol)
        
        if upstox_price is None:
            return PriceVerification(
                symbol=symbol,
                app_price=app_price,
                upstox_price=None,
                deviation_pct=None,
                verdict=PriceVerdict.UPSTOX_UNAVAILABLE,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        # Calculate deviation
        deviation = abs(app_price - upstox_price) / upstox_price
        
        # Determine verdict
        if deviation <= PRICE_DEVIATION_THRESHOLD:
            verdict = PriceVerdict.VERIFIED_REAL_PRICE
        elif deviation <= 0.05:  # 5% - likely stale
            verdict = PriceVerdict.STALE_DATA
        else:
            verdict = PriceVerdict.DATA_SOURCE_MISMATCH
        
        return PriceVerification(
            symbol=symbol,
            app_price=app_price,
            upstox_price=upstox_price,
            deviation_pct=round(deviation * 100, 3),
            verdict=verdict,
            timestamp=datetime.now(timezone.utc).isoformat()
        )


# ============================================================
# TEST RUNNER
# ============================================================
class QATestRunner:
    """Main test runner for comprehensive API testing."""
    
    def __init__(self):
        self.results: List[EndpointResult] = []
        self.jwt_token: Optional[str] = None
        self.upstox_verifier = UpstoxVerifier(UPSTOX_ACCESS_TOKEN)
    
    async def authenticate(self, session: aiohttp.ClientSession) -> bool:
        """Authenticate and get JWT token."""
        # Try to sign up first (may fail if user exists)
        try:
            async with session.post(
                f"{BASE_URL}/api/auth/signup",
                json=TEST_USER,
                timeout=10
            ) as resp:
                pass  # Ignore result
        except:
            pass
        
        # Login
        try:
            async with session.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
                timeout=10
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.jwt_token = data.get("access_token")
                    return True
        except Exception as e:
            print(f"[AUTH] Login failed: {e}")
        
        return False
    
    def classify_failure(self, status_code: int, response_data: Any, latency_ms: float) -> Tuple[FailureCategory, str]:
        """Classify failure and provide recommended fix."""
        if status_code == 200:
            return FailureCategory.NONE, ""
        
        if status_code == 422:
            return FailureCategory.VALIDATION_ERROR, "Fix request validation - check required fields and types"
        
        if status_code in (401, 403):
            return FailureCategory.AUTH_ERROR, "Check JWT token validity and authorization middleware"
        
        if status_code == 404:
            return FailureCategory.ROUTING_ERROR, "Verify endpoint path and router registration"
        
        if status_code == 504 or latency_ms > 30000:
            return FailureCategory.UPSTREAM_TIMEOUT, "Add timeout handling; consider async refactor"
        
        if status_code in (500, 503):
            error_msg = str(response_data) if response_data else ""
            if "gemini" in error_msg.lower() or "ai" in error_msg.lower():
                return FailureCategory.AI_PROVIDER_LATENCY, "Add retry logic for AI provider; implement fallback"
            if "market" in error_msg.lower() or "upstox" in error_msg.lower():
                return FailureCategory.MARKET_DATA_UNAVAILABLE, "Implement cache fallback for market data"
            return FailureCategory.INTERNAL_EXCEPTION, "Check server logs; add proper exception handling"
        
        return FailureCategory.NONE, ""
    
    def extract_stock_prices(self, endpoint: str, data: Any) -> List[Tuple[str, float]]:
        """Extract stock symbols and prices from response data."""
        prices = []
        
        if not isinstance(data, (dict, list)):
            return prices
        
        def extract_from_item(item: dict) -> Optional[Tuple[str, float]]:
            symbol = item.get("symbol") or item.get("tradingSymbol") or item.get("stock_symbol")
            price = item.get("ltp") or item.get("last_price") or item.get("close") or item.get("current_price") or item.get("price")
            
            if symbol and price:
                try:
                    # Clean symbol (remove exchange prefix if present)
                    if isinstance(symbol, str):
                        symbol = symbol.replace("NSE:", "").replace("BSE:", "").strip()
                    return (symbol, float(price))
                except:
                    pass
            return None
        
        # Handle different response structures
        if isinstance(data, list):
            for item in data[:10]:  # Limit to first 10 for efficiency
                if isinstance(item, dict):
                    result = extract_from_item(item)
                    if result:
                        prices.append(result)
        elif isinstance(data, dict):
            # Check for nested lists (gainers, losers, stocks, data, etc.)
            for key in ["gainers", "losers", "stocks", "data", "results", "signals", "snapshots"]:
                if key in data and isinstance(data[key], list):
                    for item in data[key][:5]:
                        if isinstance(item, dict):
                            result = extract_from_item(item)
                            if result:
                                prices.append(result)
            
            # Direct extraction
            result = extract_from_item(data)
            if result:
                prices.append(result)
        
        return prices
    
    async def test_endpoint(
        self, 
        session: aiohttp.ClientSession, 
        endpoint_config: dict
    ) -> EndpointResult:
        """Test a single endpoint."""
        path = endpoint_config["path"]
        method = endpoint_config["method"]
        auth_required = endpoint_config.get("auth", False)
        body = endpoint_config.get("body")
        params = endpoint_config.get("params")
        
        url = f"{BASE_URL}{path}"
        headers = {"Content-Type": "application/json"}
        
        if auth_required and self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        
        start_time = time.perf_counter()
        status_code = 0
        response_data = None
        error_message = ""
        
        try:
            if method == "GET":
                async with session.get(url, headers=headers, params=params, timeout=30) as resp:
                    status_code = resp.status
                    try:
                        response_data = await resp.json()
                    except:
                        response_data = await resp.text()
            elif method == "POST":
                async with session.post(url, headers=headers, json=body, timeout=30) as resp:
                    status_code = resp.status
                    try:
                        response_data = await resp.json()
                    except:
                        response_data = await resp.text()
            elif method == "PUT":
                async with session.put(url, headers=headers, json=body, params=params, timeout=30) as resp:
                    status_code = resp.status
                    try:
                        response_data = await resp.json()
                    except:
                        response_data = await resp.text()
            elif method == "DELETE":
                async with session.delete(url, headers=headers, timeout=30) as resp:
                    status_code = resp.status
                    try:
                        response_data = await resp.json()
                    except:
                        response_data = await resp.text()
        except asyncio.TimeoutError:
            error_message = "Request timeout (30s)"
            status_code = 504
        except Exception as e:
            error_message = str(e)
            status_code = 0
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        success = 200 <= status_code < 300
        
        # Classify failure
        failure_category, recommended_fix = self.classify_failure(status_code, response_data, latency_ms)
        
        # Extract response keys for schema validation
        response_keys = []
        if isinstance(response_data, dict):
            response_keys = list(response_data.keys())[:10]
        
        # Price verification for applicable endpoints
        price_verifications = []
        if success and path in PRICE_ENDPOINTS:
            stock_prices = self.extract_stock_prices(path, response_data)
            for symbol, app_price in stock_prices[:5]:  # Limit to 5 verifications per endpoint
                verification = await self.upstox_verifier.verify_price(session, symbol, app_price)
                price_verifications.append(verification)
                
                # Update failure category if price mismatch
                if verification.verdict in (PriceVerdict.DATA_SOURCE_MISMATCH, PriceVerdict.MOCK_OR_FAKE_DATA):
                    failure_category = FailureCategory.PRICE_MISMATCH_UPSTOX
                    recommended_fix = f"Price mismatch for {symbol}: App={app_price}, Upstox={verification.upstox_price}"
                elif verification.verdict == PriceVerdict.STALE_DATA:
                    failure_category = FailureCategory.STALE_DATA
                    recommended_fix = f"Stale data for {symbol}: {verification.deviation_pct}% deviation"
        
        return EndpointResult(
            endpoint=path,
            method=method,
            status_code=status_code,
            latency_ms=round(latency_ms, 2),
            success=success,
            failure_category=failure_category,
            error_message=error_message,
            price_verifications=price_verifications,
            response_keys=response_keys,
            recommended_fix=recommended_fix
        )
    
    async def run_all_tests(self) -> TestReport:
        """Run all endpoint tests."""
        print("=" * 60)
        print("QuantAI Comprehensive API Test Suite")
        print("=" * 60)
        print(f"Base URL: {BASE_URL}")
        print(f"Total Endpoints: {len(ENDPOINTS)}")
        print(f"Upstox Token: {'Configured' if UPSTOX_ACCESS_TOKEN else 'Not Configured'}")
        print("=" * 60)
        
        async with aiohttp.ClientSession() as session:
            # Authenticate first
            print("\n[1/3] Authenticating...")
            auth_success = await self.authenticate(session)
            print(f"  Authentication: {'SUCCESS' if auth_success else 'FAILED'}")
            
            if not auth_success:
                print("  Warning: Authenticated endpoints may fail")
            
            # Run tests
            print(f"\n[2/3] Testing {len(ENDPOINTS)} endpoints...")
            for i, endpoint in enumerate(ENDPOINTS, 1):
                result = await self.test_endpoint(session, endpoint)
                self.results.append(result)
                
                status_icon = "✓" if result.success else "✗"
                print(f"  [{i:3d}/{len(ENDPOINTS)}] {status_icon} {result.method:6s} {result.endpoint[:50]:50s} {result.status_code:3d} {result.latency_ms:8.1f}ms")
                
                # Small delay to avoid rate limiting
                if i % 10 == 0:
                    await asyncio.sleep(0.1)
            
            # Generate report
            print("\n[3/3] Generating report...")
        
        return self.generate_report()
    
    def generate_report(self) -> TestReport:
        """Generate test report."""
        latencies = [r.latency_ms for r in self.results if r.status_code > 0]
        
        passed = sum(1 for r in self.results if r.success)
        failed = len(self.results) - passed
        
        avg_latency = statistics.mean(latencies) if latencies else 0
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
        
        endpoints_over_target = sum(1 for l in latencies if l > TARGET_LATENCY_MS)
        
        # Count price verifications
        all_verifications = []
        for r in self.results:
            all_verifications.extend(r.price_verifications)
        
        price_passed = sum(1 for v in all_verifications if v.verdict == PriceVerdict.VERIFIED_REAL_PRICE)
        
        return TestReport(
            run_timestamp=datetime.now(timezone.utc).isoformat(),
            total_endpoints=len(self.results),
            passed=passed,
            failed=failed,
            avg_latency_ms=round(avg_latency, 2),
            p95_latency_ms=round(p95_latency, 2),
            endpoints_over_target=endpoints_over_target,
            price_verifications_total=len(all_verifications),
            price_verifications_passed=price_passed,
            results=self.results
        )


# ============================================================
# REPORT GENERATION
# ============================================================
def generate_markdown_report(report: TestReport, output_path: Path) -> None:
    """Generate a Markdown report."""
    
    lines = [
        "# QuantAI API Test Report",
        "",
        f"**Run Timestamp:** {report.run_timestamp}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Endpoints | {report.total_endpoints} |",
        f"| Passed | {report.passed} |",
        f"| Failed | {report.failed} |",
        f"| Pass Rate | {report.passed/report.total_endpoints*100:.1f}% |",
        f"| Avg Latency | {report.avg_latency_ms:.1f}ms |",
        f"| P95 Latency | {report.p95_latency_ms:.1f}ms |",
        f"| Endpoints > 2s | {report.endpoints_over_target} |",
        f"| Price Verifications | {report.price_verifications_passed}/{report.price_verifications_total} |",
        "",
    ]
    
    # Failed endpoints
    failed = [r for r in report.results if not r.success]
    if failed:
        lines.extend([
            "## Failed Endpoints",
            "",
            "| Endpoint | Status | Latency | Category | Fix |",
            "|----------|--------|---------|----------|-----|",
        ])
        for r in failed:
            lines.append(f"| `{r.method} {r.endpoint}` | {r.status_code} | {r.latency_ms:.0f}ms | {r.failure_category.value} | {r.recommended_fix[:50]} |")
        lines.append("")
    
    # Slow endpoints
    slow = [r for r in report.results if r.latency_ms > TARGET_LATENCY_MS]
    if slow:
        lines.extend([
            "## Slow Endpoints (>2s)",
            "",
            "| Endpoint | Latency | Recommendation |",
            "|----------|---------|----------------|",
        ])
        for r in sorted(slow, key=lambda x: -x.latency_ms):
            lines.append(f"| `{r.method} {r.endpoint}` | {r.latency_ms:.0f}ms | Consider async refactor or caching |")
        lines.append("")
    
    # Price Verifications
    all_verifications = []
    for r in report.results:
        for v in r.price_verifications:
            all_verifications.append((r.endpoint, v))
    
    if all_verifications:
        lines.extend([
            "## Price Verification Results",
            "",
            "| Endpoint | Symbol | App Price | Upstox Price | Deviation | Verdict |",
            "|----------|--------|-----------|--------------|-----------|---------|",
        ])
        for endpoint, v in all_verifications:
            upstox_str = f"₹{v.upstox_price:.2f}" if v.upstox_price else "N/A"
            dev_str = f"{v.deviation_pct:.2f}%" if v.deviation_pct is not None else "N/A"
            verdict_emoji = "✅" if v.verdict == PriceVerdict.VERIFIED_REAL_PRICE else "❌"
            if v.verdict == PriceVerdict.UPSTOX_UNAVAILABLE:
                verdict_emoji = "⚠️"
            lines.append(f"| `{endpoint[:30]}` | {v.symbol} | ₹{v.app_price:.2f} | {upstox_str} | {dev_str} | {verdict_emoji} {v.verdict.value} |")
        lines.append("")
    
    # All endpoints table
    lines.extend([
        "## All Endpoints",
        "",
        "| # | Endpoint | Method | Status | Latency | Result |",
        "|---|----------|--------|--------|---------|--------|",
    ])
    for i, r in enumerate(report.results, 1):
        result_emoji = "✅" if r.success else "❌"
        lines.append(f"| {i} | `{r.endpoint[:40]}` | {r.method} | {r.status_code} | {r.latency_ms:.0f}ms | {result_emoji} |")
    
    # Write report
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport saved to: {output_path}")


def generate_json_report(report: TestReport, output_path: Path) -> None:
    """Generate a JSON report."""
    
    def serialize(obj):
        if isinstance(obj, Enum):
            return obj.value
        if hasattr(obj, '__dict__'):
            return {k: serialize(v) for k, v in obj.__dict__.items()}
        if isinstance(obj, list):
            return [serialize(i) for i in obj]
        return obj
    
    data = serialize(report)
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"JSON report saved to: {output_path}")


# ============================================================
# MAIN
# ============================================================
async def main():
    runner = QATestRunner()
    report = await runner.run_all_tests()
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total: {report.total_endpoints}")
    print(f"Passed: {report.passed} ({report.passed/report.total_endpoints*100:.1f}%)")
    print(f"Failed: {report.failed}")
    print(f"Avg Latency: {report.avg_latency_ms:.1f}ms")
    print(f"P95 Latency: {report.p95_latency_ms:.1f}ms")
    print(f"Price Verifications: {report.price_verifications_passed}/{report.price_verifications_total}")
    print("=" * 60)
    
    # Generate reports
    backend_dir = Path(__file__).parent
    generate_markdown_report(report, backend_dir / "qa_test_report.md")
    generate_json_report(report, backend_dir / "qa_test_results.json")
    
    # Exit code based on success
    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
