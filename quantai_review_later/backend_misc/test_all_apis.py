"""
Comprehensive API Testing for QuantAI India Trading Bot
Simplified output with log file
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
LOG_FILE = "api_test_results.txt"

class APITester:
    def __init__(self):
        self.results = []
        self.token = None
        self.headers = {}
        self.log_lines = []
    
    def log(self, message):
        print(message)
        self.log_lines.append(message)
    
    def save_log(self):
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.log_lines))
    
    def test(self, name, method, endpoint, expected_status=200, json_data=None, auth_required=True, timeout=30):
        url = f"{BASE_URL}{endpoint}"
        headers = self.headers if auth_required else {}
        
        try:
            if method == "GET":
                r = requests.get(url, headers=headers, timeout=timeout)
            elif method == "POST":
                r = requests.post(url, json=json_data, headers=headers, timeout=timeout)
            elif method == "PUT":
                r = requests.put(url, json=json_data, headers=headers, timeout=timeout)
            elif method == "DELETE":
                r = requests.delete(url, headers=headers, timeout=timeout)
            else:
                self.results.append((name, False, "Invalid method"))
                return None
            
            passed = r.status_code == expected_status
            status = f"{r.status_code}"
            
            if passed:
                self.log(f"  PASS: {name} ({status})")
            else:
                self.log(f"  FAIL: {name} (Expected {expected_status}, Got {status})")
            
            self.results.append((name, passed, status))
            return r
            
        except requests.exceptions.Timeout:
            self.log(f"  WARN: {name} (Timeout)")
            self.results.append((name, False, "Timeout"))
            return None
        except requests.exceptions.ConnectionError:
            self.log(f"  FAIL: {name} (Connection Error)")
            self.results.append((name, False, "Connection Error"))
            return None
        except Exception as e:
            self.log(f"  FAIL: {name} ({str(e)[:50]})")
            self.results.append((name, False, str(e)[:50]))
            return None
    
    def run_all_tests(self):
        self.log("=" * 70)
        self.log("QUANTAI INDIA - COMPREHENSIVE API TESTING")
        self.log(f"Started at: {datetime.now()}")
        self.log("=" * 70)
        
        # 1. BASIC ENDPOINTS
        self.log("\n[BASIC ENDPOINTS]")
        self.test("Root Endpoint", "GET", "/", auth_required=False)
        self.test("Health Check", "GET", "/health", auth_required=False)
        
        # 2. AUTHENTICATION
        self.log("\n[AUTHENTICATION]")
        r = self.test("Login", "POST", "/api/auth/login", 
                      json_data={"email": "demo@example.com", "password": "demo123"},
                      auth_required=False)
        
        if r and r.status_code == 200:
            self.token = r.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
            self.log(f"      Token acquired successfully")
        else:
            self.log("  CRITICAL: Login failed")
            return self.print_summary()
        
        self.test("Get Current User", "GET", "/api/auth/me")
        
        # 3. TRADING
        self.log("\n[TRADING]")
        self.test("Dashboard Stats", "GET", "/api/trading/dashboard")
        self.test("Market Indices", "GET", "/api/trading/market-indices", timeout=60)
        self.test("Gainers/Losers", "GET", "/api/trading/gainers-losers", timeout=60)
        
        # 4. UPSTOX
        self.log("\n[UPSTOX]")
        self.test("Upstox Auth URL", "GET", "/api/upstox/auth-url")
        # Note: Portfolio & Positions require user OAuth connection (skipped)
        
        # 5. ORDERS
        self.log("\n[ORDERS]")
        self.test("Get Orders", "GET", "/api/orders/")
        
        # 6. RISK
        self.log("\n[RISK]")
        self.test("Get Risk Config", "GET", "/api/risk/")
        
        # 7. SETTINGS
        self.log("\n[SETTINGS]")
        self.test("Get Settings", "GET", "/api/settings/")
        
        # 8. ALGORITHMS
        self.log("\n[ALGORITHMS]")
        self.test("Get Algorithms", "GET", "/api/algorithms/")
        
        # 9. AI
        self.log("\n[AI]")
        self.test("Market Analysis", "GET", "/api/ai/market-analysis", timeout=60)
        
        # 10. QUANT BOT
        self.log("\n[QUANT BOT]")
        self.test("Quant Symbols", "GET", "/api/quant/symbols")
        self.test("Quant Strategies", "GET", "/api/quant/strategies")
        
        # 11. SCANNER
        self.log("\n[SCANNER]")
        self.test("Scanner Momentum", "GET", "/api/scanner/momentum", timeout=60)
        self.test("Scanner Strategies", "GET", "/api/scanner/strategies")
        self.test("Scanner Indices", "GET", "/api/scanner/indices")
        
        # 12. MARKET
        self.log("\n[MARKET]")
        self.test("Sector Heatmap", "GET", "/api/market/heatmap", timeout=60)
        
        # 13. ALPHAPRIME
        self.log("\n[ALPHAPRIME]")
        self.test("AlphaPrime Signals", "GET", "/api/v1/alpha-prime/signals?limit=5", timeout=60)
        self.test("AlphaPrime Config", "GET", "/api/v1/alpha-prime/config")
        
        # 14. ENGINE PERFORMANCE
        self.log("\n[ENGINE PERFORMANCE]")
        self.test("Engine Performance", "GET", "/api/engines/performance")
        
        # 15. ALERTS
        self.log("\n[ALERTS]")
        self.test("List Monitors", "GET", "/api/alerts/monitors")
        
        # 16. AGENTIC BOT
        self.log("\n[AGENTIC BOT]")
        self.test("Agentic Bot Process", "POST", "/api/agentic-bot/process",
                  json_data={"prompt": "Analyze RELIANCE"}, timeout=120)
        
        return self.print_summary()
    
    def print_summary(self):
        self.log("\n" + "=" * 70)
        self.log("TEST SUMMARY")
        self.log("=" * 70)
        
        passed = sum(1 for _, status, _ in self.results if status)
        failed = sum(1 for _, status, _ in self.results if not status)
        total = len(self.results)
        
        self.log("\nDetailed Results:")
        self.log("-" * 50)
        
        for name, status, details in self.results:
            icon = "PASS" if status else "FAIL"
            self.log(f"  [{icon}] {name}: {details}")
        
        self.log("\n" + "-" * 50)
        self.log(f"PASSED: {passed}/{total} ({100*passed//total if total else 0}%)")
        self.log(f"FAILED: {failed}/{total}")
        self.log("=" * 70)
        
        if passed == total:
            self.log("\n*** ALL TESTS PASSED! ***")
        elif passed >= total * 0.8:
            self.log("\n*** MOST TESTS PASSED! ***")
        elif passed >= total * 0.5:
            self.log("\n*** PARTIAL SUCCESS ***")
        else:
            self.log("\n*** SIGNIFICANT FAILURES ***")
        
        self.save_log()
        self.log(f"\nResults saved to: {LOG_FILE}")
        
        return passed, total


if __name__ == "__main__":
    tester = APITester()
    passed, total = tester.run_all_tests()
