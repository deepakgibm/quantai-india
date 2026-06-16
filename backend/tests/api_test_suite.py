"""
Comprehensive Backend API Test Suite
Tests all endpoints and creates a summary report
Updated to use correct endpoint paths based on router analysis
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
TEST_EMAIL = "dthat53@gmail.com"
TEST_PASSWORD = "admin1243"

# Results tracker
results = []

def log_result(category, endpoint, method, status_code, success, response_time_ms, notes=""):
    results.append({
        "category": category,
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "success": success,
        "response_time_ms": round(response_time_ms, 2),
        "notes": notes[:100] if notes else ""
    })
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status} [{method}] {endpoint} - {status_code} ({response_time_ms:.0f}ms)")

def test_endpoint(category, endpoint, method="GET", headers=None, data=None, expected_codes=[200]):
    try:
        start = time.time()
        if method == "GET":
            resp = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=60)
        elif method == "POST":
            resp = requests.post(f"{BASE_URL}{endpoint}", headers=headers, json=data, timeout=60)
        elif method == "PUT":
            resp = requests.put(f"{BASE_URL}{endpoint}", headers=headers, json=data, timeout=60)
        elif method == "DELETE":
            resp = requests.delete(f"{BASE_URL}{endpoint}", headers=headers, timeout=60)
        elapsed_ms = (time.time() - start) * 1000
        
        success = resp.status_code in expected_codes
        notes = ""
        if not success:
            try:
                notes = resp.text[:100]
            except:
                notes = "Error parsing response"
        
        log_result(category, endpoint, method, resp.status_code, success, elapsed_ms, notes)
        return resp
    except requests.exceptions.ConnectionError:
        log_result(category, endpoint, method, 0, False, 0, "Connection refused")
        return None
    except requests.exceptions.Timeout:
        log_result(category, endpoint, method, 0, False, 30000, "Timeout")
        return None
    except Exception as e:
        log_result(category, endpoint, method, 0, False, 0, str(e))
        return None

def main():
    print("=" * 60)
    print("BACKEND API TEST SUITE")
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Base URL: {BASE_URL}")
    print("=" * 60)
    
    # 1. Health Check
    print("\n--- HEALTH CHECK ---")
    test_endpoint("Health", "/health", expected_codes=[200, 503])
    test_endpoint("Health", "/ready", expected_codes=[200, 503])
    
    # 2. Authentication
    print("\n--- AUTHENTICATION ---")
    login_resp = test_endpoint("Auth", "/api/auth/login", "POST", 
                               data={"email": TEST_EMAIL, "password": TEST_PASSWORD},
                               expected_codes=[200])
    
    token = None
    if login_resp and login_resp.status_code == 200:
        try:
            token = login_resp.json().get("access_token")
            print(f"   Token acquired: {token[:20]}...")
        except:
            print("   Failed to parse token")
    
    auth_headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    # Test auth endpoints
    test_endpoint("Auth", "/api/auth/me", headers=auth_headers, expected_codes=[200, 401])
    
    # 3. Market Data Endpoints
    print("\n--- MARKET DATA ---")
    test_endpoint("Market", "/api/market/top-movers", expected_codes=[200])
    test_endpoint("Market", "/api/market/global-context", expected_codes=[200])
    test_endpoint("Market", "/api/market/status", expected_codes=[200])
    test_endpoint("Market", "/api/market/orchestrator-status", headers=auth_headers, expected_codes=[200])
    
    # 4. Trading Dashboard
    print("\n--- TRADING ---")
    test_endpoint("Trading", "/api/trading/dashboard", headers=auth_headers, expected_codes=[200])
    test_endpoint("Trading", "/api/trading/indices", expected_codes=[200])
    test_endpoint("Trading", "/api/trading/instruments", expected_codes=[200])
    test_endpoint("Trading", "/api/trading/top-gainers", headers=auth_headers, expected_codes=[200])
    
    # 5. Scanner API
    print("\n--- SCANNER ---")
    test_endpoint("Scanner", "/api/scanner/strategies", headers=auth_headers, expected_codes=[200])
    test_endpoint("Scanner", "/api/scanner/momentum", headers=auth_headers, expected_codes=[200])
    test_endpoint("Scanner", "/api/scanner/week52-breakouts", headers=auth_headers, expected_codes=[200])
    test_endpoint("Scanner", "/api/scanner/hp/momentum", headers=auth_headers, expected_codes=[200])
    test_endpoint("Scanner", "/api/scanner/hp/breakout", headers=auth_headers, expected_codes=[200])
    
    # 6. Heatmap & Sector Endpoints
    print("\n--- HEATMAP & SECTOR ANALYSIS ---")
    test_endpoint("Heatmap", "/api/heatmap?mode=performance&timeframe=1D", headers=auth_headers, expected_codes=[200])
    test_endpoint("SectorAnalysis", "/api/sector-analysis?timeframe=1D", headers=auth_headers, expected_codes=[200])
    
    # 7. AI Endpoints
    print("\n--- AI ENDPOINTS ---")
    test_endpoint("AI", "/api/ai/strategies", headers=auth_headers, expected_codes=[200])
    test_endpoint("AI", "/api/ai/breakout-detector", headers=auth_headers, expected_codes=[200])
    test_endpoint("AI", "/api/ai/trend-finder", headers=auth_headers, expected_codes=[200])
    test_endpoint("AI", "/api/ai/top5-picks", headers=auth_headers, expected_codes=[200])
    test_endpoint("AI", "/api/ai/market-analysis", headers=auth_headers, expected_codes=[200])
    test_endpoint("AI", "/api/ai/sentiment", headers=auth_headers, expected_codes=[200])
    
    # 8. Analytics
    print("\n--- ANALYTICS ---")
    test_endpoint("Analytics", "/api/analytics/overview", headers=auth_headers, expected_codes=[200])
    test_endpoint("Analytics", "/api/analytics/indicators/latest/RELIANCE", headers=auth_headers, expected_codes=[200])
    test_endpoint("Analytics", "/api/analytics/volatility/RELIANCE", headers=auth_headers, expected_codes=[200])
    
    # 9. SaaS Subscription
    print("\n--- SAAS SUBSCRIPTION ---")
    test_endpoint("SaaS", "/api/saas/subscription", headers=auth_headers, expected_codes=[200])
    
    # 10. Engine Performance
    print("\n--- ENGINE PERFORMANCE ---")
    test_endpoint("Engine", "/api/engines/performance", headers=auth_headers, expected_codes=[200])
    
    # 11. Watchlist
    print("\n--- WATCHLIST ---")
    test_endpoint("Watchlist", "/api/watchlist/", headers=auth_headers, expected_codes=[200])
    
    # 12. Upstox
    print("\n--- UPSTOX ---")
    test_endpoint("Upstox", "/api/upstox/status", expected_codes=[200])
    test_endpoint("Upstox", "/api/upstox/connect-url", expected_codes=[200])
    
    # 13. Search
    print("\n--- SEARCH ---")
    test_endpoint("Search", "/api/search/stocks?q=RELIANCE", headers=auth_headers, expected_codes=[200])

    
    # Print Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed} ({100*passed/total:.1f}%)")
    print(f"Failed: {failed}")
    print()
    
    # Group by category
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"passed": 0, "failed": 0, "endpoints": []}
        if r["success"]:
            categories[cat]["passed"] += 1
        else:
            categories[cat]["failed"] += 1
        categories[cat]["endpoints"].append(r)
    
    print("Results by Category:")
    for cat, data in categories.items():
        status = "[PASS]" if data["failed"] == 0 else "[WARN]" if data["passed"] > 0 else "[FAIL]"
        print(f"  {status} {cat}: {data['passed']}/{data['passed']+data['failed']} passed")
    
    # Show failed tests
    failed_tests = [r for r in results if not r["success"]]
    if failed_tests:
        print("\nFailed Tests:")
        for r in failed_tests:
            print(f"  [FAIL] [{r['method']}] {r['endpoint']} - {r['status_code']} - {r['notes']}")
    
    # Save results to JSON
    with open("api_test_results.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {"total": total, "passed": passed, "failed": failed},
            "results": results
        }, f, indent=2)
    
    print(f"\nResults saved to api_test_results.json")
    
    return passed, failed

if __name__ == "__main__":
    main()
