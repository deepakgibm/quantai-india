"""
Full-Stack Backend API Testing Script
Tests all major API endpoints against Docker runtime
"""

import httpx
import asyncio
from datetime import datetime
from typing import Dict, List
import sys

BASE_URL = "http://localhost:8000"

class APITester:
    def __init__(self):
        self.results: List[Dict] = []
        self.passed = 0
        self.failed = 0
        
    async def test_endpoint(
        self,
        method: str,
        path: str,
        expected_status: int = 200,
        payload: Dict = None,
        headers: Dict = None,
        description: str = ""
    ) -> Dict:
        """Test a single API endpoint."""
        url = f"{BASE_URL}{path}"
        result = {
            "method": method,
            "path": path,
            "description": description,
            "expected_status": expected_status,
            "actual_status": None,
            "response_time_ms": None,
            "success": False,
            "error": None,
            "response_snippet": None
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                start = datetime.now()
                
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, json=payload, headers=headers)
                elif method == "PUT":
                    response = await client.put(url, json=payload, headers=headers)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    result["error"] = f"Unknown method: {method}"
                    return result
                
                end = datetime.now()
                result["response_time_ms"] = (end - start).total_seconds() * 1000
                result["actual_status"] = response.status_code
                
                # Get response snippet
                try:
                    resp_json = response.json()
                    result["response_snippet"] = str(resp_json)[:200]
                except:
                    result["response_snippet"] = response.text[:200]
                
                # Check if status matches expected
                if response.status_code == expected_status:
                    result["success"] = True
                    self.passed += 1
                else:
                    result["success"] = False
                    self.failed += 1
                    
        except httpx.ConnectError as e:
            result["error"] = f"Connection failed: {str(e)}"
            self.failed += 1
        except httpx.TimeoutException:
            result["error"] = "Request timeout"
            self.failed += 1
        except Exception as e:
            result["error"] = str(e)
            self.failed += 1
            
        self.results.append(result)
        return result
    
    def print_results(self):
        """Print test results in a formatted table."""
        print("\n" + "=" * 100)
        print("BACKEND API TEST RESULTS")
        print("=" * 100)
        print(f"\n{'#':<4} {'Method':<8} {'Path':<45} {'Status':<10} {'Time(ms)':<10} {'Result':<8}")
        print("-" * 100)
        
        for i, r in enumerate(self.results, 1):
            status = f"{r['actual_status'] or 'ERR'}/{r['expected_status']}"
            time_ms = f"{r['response_time_ms']:.1f}" if r['response_time_ms'] else "N/A"
            result = "✓ PASS" if r['success'] else "✗ FAIL"
            
            print(f"{i:<4} {r['method']:<8} {r['path']:<45} {status:<10} {time_ms:<10} {result:<8}")
            if r['error']:
                print(f"     └─ Error: {r['error']}")
        
        print("\n" + "=" * 100)
        print(f"SUMMARY: {self.passed} passed, {self.failed} failed, {len(self.results)} total")
        print("=" * 100)


async def main():
    tester = APITester()
    
    print("\n🚀 Starting Backend API Tests...")
    print(f"Base URL: {BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # ============================================
    # HEALTH & SYSTEM ENDPOINTS
    # ============================================
    print("\n📊 Testing Health & System Endpoints...")
    
    await tester.test_endpoint("GET", "/", 200, description="Root endpoint")
    await tester.test_endpoint("GET", "/health", 200, description="Health check")
    await tester.test_endpoint("GET", "/ready", 200, description="Readiness check")
    
    # ============================================
    # AUTHENTICATION ENDPOINTS
    # ============================================
    print("\n🔐 Testing Authentication Endpoints...")
    
    await tester.test_endpoint("GET", "/api/auth/me", 401, description="Get current user (no auth)")
    await tester.test_endpoint("POST", "/api/auth/login", 422, description="Login (missing data)")
    await tester.test_endpoint("POST", "/api/auth/signup", 422, description="Signup (missing data)")
    
    # ============================================
    # TRADING ENDPOINTS
    # ============================================
    print("\n📈 Testing Trading Endpoints...")
    
    await tester.test_endpoint("GET", "/api/trading/market-indices", 200, description="Market indices")
    await tester.test_endpoint("GET", "/api/trading/instruments", 200, description="Trading instruments")
    await tester.test_endpoint("GET", "/api/trading/health", 200, description="Trading health")
    
    # ============================================
    # AI STRATEGY ENDPOINTS
    # ============================================
    print("\n🤖 Testing AI Strategy Endpoints...")
    
    await tester.test_endpoint("GET", "/api/ai/strategies", 200, description="AI strategies list")
    await tester.test_endpoint("GET", "/api/ai/trend-finder", 200, description="Trend Finder AI")
    await tester.test_endpoint("GET", "/api/ai/breakout", 200, description="Breakout Detector")
    await tester.test_endpoint("GET", "/api/ai/top5-picks", 200, description="Top 5 Picks")
    await tester.test_endpoint("GET", "/api/ai/momentum-scanner", 200, description="Momentum Scanner")
    await tester.test_endpoint("GET", "/api/ai/mean-reversion", 200, description="Mean Reversion")
    await tester.test_endpoint("GET", "/api/ai/market-analysis", 200, description="Market Analysis")
    
    # ============================================
    # MARKET DATA ENDPOINTS
    # ============================================
    print("\n📊 Testing Market Data Endpoints...")
    
    await tester.test_endpoint("GET", "/api/market/nifty100/top-movers", 200, description="NIFTY 100 Top Movers")
    await tester.test_endpoint("GET", "/api/market/nifty100/status", 200, description="NIFTY 100 Status")
    await tester.test_endpoint("GET", "/api/market/sector-heatmap", 200, description="Sector Heatmap")
    await tester.test_endpoint("GET", "/api/market/health", 200, description="Market Health")
    
    # ============================================
    # SCANNER ENDPOINTS
    # ============================================
    print("\n🔍 Testing Scanner Endpoints...")
    
    await tester.test_endpoint("GET", "/api/scanner/strategies", 200, description="Scanner Strategies")
    await tester.test_endpoint("GET", "/api/scanner/indices", 200, description="Scanner Indices")
    await tester.test_endpoint("GET", "/api/scanner/timeframes", 200, description="Scanner Timeframes")
    await tester.test_endpoint("GET", "/api/scanner/momentum", 200, description="Momentum Data")
    await tester.test_endpoint("GET", "/api/scanner/breakout", 200, description="Breakout Data")
    await tester.test_endpoint("GET", "/api/scanner/reversal", 200, description="Reversal Data")
    await tester.test_endpoint("GET", "/api/scanner/52week", 200, description="52-Week Breakouts")
    
    # ============================================
    # HP SCANNER V3 ENDPOINTS
    # ============================================
    print("\n⚡ Testing HP Scanner v3 Endpoints...")
    
    await tester.test_endpoint("GET", "/api/v3/scanner/momentum", 200, description="HP Momentum")
    await tester.test_endpoint("GET", "/api/v3/scanner/breakout", 200, description="HP Breakout")
    await tester.test_endpoint("GET", "/api/v3/scanner/reversal", 200, description="HP Reversal")
    await tester.test_endpoint("GET", "/api/v3/scanner/snapshots", 200, description="HP Snapshots")
    await tester.test_endpoint("GET", "/api/v3/scanner/status", 200, description="HP Status")
    await tester.test_endpoint("GET", "/api/v3/scanner/metrics", 200, description="HP Metrics")
    
    # ============================================
    # HEATMAP ENDPOINTS
    # ============================================
    print("\n🗺️ Testing Heatmap Endpoints...")
    
    await tester.test_endpoint("GET", "/api/heatmap/sectors", 200, description="Heatmap Sectors")
    await tester.test_endpoint("GET", "/api/heatmap/sector/Banking", 200, description="Banking Sector Stocks")
    
    # ============================================
    # QUANT BOT ENDPOINTS
    # ============================================
    print("\n🔬 Testing Quant Bot Endpoints...")
    
    await tester.test_endpoint("GET", "/api/quant/strategies", 200, description="Quant Strategies")
    await tester.test_endpoint("GET", "/api/quant/symbols", 200, description="Available Symbols")
    
    # ============================================
    # ANALYTICS ENDPOINTS
    # ============================================
    print("\n📉 Testing Analytics Endpoints...")
    
    await tester.test_endpoint("GET", "/api/analytics/overview", 200, description="Analytics Overview")
    await tester.test_endpoint("GET", "/api/analytics/momentum?n=10", 200, description="Top Momentum")
    await tester.test_endpoint("GET", "/api/analytics/volatility/RELIANCE", 200, description="Volatility Analysis")
    await tester.test_endpoint("GET", "/api/analytics/archives", 200, description="Archive List")
    
    # ============================================
    # WALK-FORWARD BACKTEST ENDPOINTS
    # ============================================
    print("\n📊 Testing Walk-Forward Backtest Endpoints...")
    
    await tester.test_endpoint("GET", "/api/v1/walk-forward/strategies", 200, description="WF Strategies")
    await tester.test_endpoint("GET", "/api/v1/walk-forward/presets", 200, description="WF Presets")
    await tester.test_endpoint("GET", "/api/v1/walk-forward/symbols?timeframe=1D", 200, description="WF Symbols (Daily)")
    
    # ============================================
    # UPSTOX ENDPOINTS
    # ============================================
    print("\n🔗 Testing Upstox Endpoints...")
    
    await tester.test_endpoint("GET", "/api/upstox/status", 200, description="Upstox Status")
    await tester.test_endpoint("GET", "/api/upstox/user-profile", 200, description="User Profile (Guest)")
    await tester.test_endpoint("GET", "/api/upstox/portfolio", 200, description="Portfolio (Guest)")
    
    # ============================================
    # ENGINE PERFORMANCE ENDPOINTS
    # ============================================
    print("\n⚙️ Testing Engine Performance Endpoints...")
    
    await tester.test_endpoint("GET", "/api/engines/test", 200, description="Engine Test")
    await tester.test_endpoint("GET", "/api/engines/performance", 200, description="Engine Performance")
    
    # ============================================
    # RISK & SETTINGS ENDPOINTS
    # ============================================
    print("\n⚠️ Testing Risk & Settings Endpoints...")
    
    await tester.test_endpoint("GET", "/api/risk/", 200, description="Risk Settings (Guest)")
    await tester.test_endpoint("GET", "/api/settings/", 200, description="User Settings (Guest)")
    
    # ============================================
    # ALGORITHMS ENDPOINTS
    # ============================================
    print("\n🧮 Testing Algorithms Endpoints...")
    
    await tester.test_endpoint("GET", "/api/algorithms/", 200, description="Algorithms List (Guest)")
    
    # ============================================
    # ORDERS ENDPOINTS
    # ============================================
    print("\n📝 Testing Orders Endpoints...")
    
    await tester.test_endpoint("GET", "/api/orders/", 200, description="Orders List (Guest)")
    
    # Print final results
    tester.print_results()
    
    # Return exit code based on failures
    return 0 if tester.failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
