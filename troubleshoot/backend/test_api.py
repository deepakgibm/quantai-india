"""
QuantAI Backend API Test Suite
Comprehensive API testing with authentication
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
CREDENTIALS = {"email": "dthat53@gmail.com", "password": "admin1243"}

# Test results storage
results = []

def log_result(endpoint, method, status, success, response_time, notes=""):
    results.append({
        "endpoint": endpoint,
        "method": method,
        "status": status,
        "success": success,
        "response_time_ms": round(response_time * 1000, 2),
        "notes": notes
    })
    icon = "✅" if success else "❌"
    print(f"{icon} {method} {endpoint} - {status} ({response_time*1000:.0f}ms) {notes}")

def test_endpoint(url, method="GET", headers=None, json_data=None, timeout=15):
    start = time.time()
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=timeout)
        elif method == "POST":
            r = requests.post(url, headers=headers, json=json_data, timeout=timeout)
        elapsed = time.time() - start
        return r, elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"DEBUG: Exception for {url}: {e}")
        return None, elapsed

# ===================== TESTS =====================

print("=" * 60)
print("QuantAI API Test Suite")
print(f"Started: {datetime.now().isoformat()}")
print("=" * 60)

# 1. Health Check
r, t = test_endpoint(f"{BASE_URL}/health")
if r:
    log_result("/health", "GET", r.status_code, r.status_code == 200, t)
else:
    log_result("/health", "GET", "ERROR", False, t, "Connection failed")

# 2. Ready Check
r, t = test_endpoint(f"{BASE_URL}/ready")
if r:
    log_result("/ready", "GET", r.status_code, r.status_code == 200, t)
else:
    log_result("/ready", "GET", "ERROR", False, t)

# 3. Authentication
r, t = test_endpoint(f"{BASE_URL}/api/auth/login", "POST", json_data=CREDENTIALS)
token = None
if r and r.status_code == 200:
    token = r.json().get("access_token")
    log_result("/api/auth/login", "POST", 200, True, t, "Token received")
else:
    log_result("/api/auth/login", "POST", r.status_code if r else "ERROR", False, t)

if not token:
    print("\n❌ FATAL: No auth token - cannot continue tests")
    exit(1)

# Auth headers for subsequent requests
auth_headers = {"Authorization": f"Bearer {token}"}

# 4. User Profile
r, t = test_endpoint(f"{BASE_URL}/api/auth/me", headers=auth_headers)
if r:
    log_result("/api/auth/me", "GET", r.status_code, r.status_code == 200, t)
else:
    log_result("/api/auth/me", "GET", "ERROR", False, t)

# 5. Scanner Strategies
r, t = test_endpoint(f"{BASE_URL}/api/scanner/strategies", headers=auth_headers)
if r:
    data = r.json() if r.status_code == 200 else {}
    count = len(data.get("strategies", {}))
    log_result("/api/scanner/strategies", "GET", r.status_code, r.status_code == 200, t, f"{count} strategy tiers")
else:
    log_result("/api/scanner/strategies", "GET", "ERROR", False, t)

# 6. Market Indices
r, t = test_endpoint(f"{BASE_URL}/api/market/indices", headers=auth_headers)
if r:
    log_result("/api/market/indices", "GET", r.status_code, r.status_code in [200, 503], t)
else:
    log_result("/api/market/indices", "GET", "ERROR", False, t)

# 7. AI Strategies
r, t = test_endpoint(f"{BASE_URL}/api/ai/strategies", headers=auth_headers)
if r:
    log_result("/api/ai/strategies", "GET", r.status_code, r.status_code == 200, t)
else:
    log_result("/api/ai/strategies", "GET", "ERROR", False, t)

# 8. Top 5 Picks
r, t = test_endpoint(f"{BASE_URL}/api/ai/top5-picks", headers=auth_headers, timeout=30)
if r:
    data = r.json() if r.status_code == 200 else {}
    count = data.get("count", 0)
    log_result("/api/ai/top5-picks", "GET", r.status_code, r.status_code == 200, t, f"{count} signals")
else:
    log_result("/api/ai/top5-picks", "GET", "ERROR", False, t)

# 9. Trend Finder
r, t = test_endpoint(f"{BASE_URL}/api/ai/trend-finder", headers=auth_headers, timeout=30)
if r:
    log_result("/api/ai/trend-finder", "GET", r.status_code, r.status_code == 200, t)
else:
    log_result("/api/ai/trend-finder", "GET", "ERROR", False, t)

# 10. Breakout Detector
r, t = test_endpoint(f"{BASE_URL}/api/ai/breakout-detector", headers=auth_headers, timeout=30)
if r:
    log_result("/api/ai/breakout-detector", "GET", r.status_code, r.status_code == 200, t)
else:
    log_result("/api/ai/breakout-detector", "GET", "ERROR", False, t)

# 11. Momentum Scanner
r, t = test_endpoint(f"{BASE_URL}/api/ai/momentum-scanner", headers=auth_headers, timeout=30)
if r:
    log_result("/api/ai/momentum-scanner", "GET", r.status_code, r.status_code == 200, t)
else:
    log_result("/api/ai/momentum-scanner", "GET", "ERROR", False, t)

# 12. Heatmap Sectors
r, t = test_endpoint(f"{BASE_URL}/api/heatmap/sectors", headers=auth_headers)
if r:
    log_result("/api/heatmap/sectors", "GET", r.status_code, r.status_code in [200, 503], t)
else:
    log_result("/api/heatmap/sectors", "GET", "ERROR", False, t)

# 13. Engine Performance
r, t = test_endpoint(f"{BASE_URL}/api/engines/performance", headers=auth_headers)
if r:
    log_result("/api/engines/performance", "GET", r.status_code, r.status_code == 200, t)
else:
    log_result("/api/engines/performance", "GET", "ERROR", False, t)

# 14. Dashboard Stats
r, t = test_endpoint(f"{BASE_URL}/api/trading/dashboard", headers=auth_headers)
if r:
    log_result("/api/trading/dashboard", "GET", r.status_code, r.status_code == 200, t)
else:
    log_result("/api/trading/dashboard", "GET", "ERROR", False, t)

# 15. Week 52 Breakouts
r, t = test_endpoint(f"{BASE_URL}/api/scanner/week52-breakouts", headers=auth_headers, timeout=30)
if r:
    log_result("/api/scanner/week52-breakouts", "GET", r.status_code, r.status_code in [200, 503], t)
else:
    log_result("/api/scanner/week52-breakouts", "GET", "ERROR", False, t)

# 16. Backtest Strategies List
r, t = test_endpoint(f"{BASE_URL}/api/v1/backtest/strategies", headers=auth_headers)
if r:
    log_result("/api/v1/backtest/strategies", "GET", r.status_code, r.status_code == 200, t)
else:
    log_result("/api/v1/backtest/strategies", "GET", "ERROR", False, t)

# 17. NIFTY 100 Top Movers
r, t = test_endpoint(f"{BASE_URL}/api/market/nifty100/top-movers", headers=auth_headers)
if r:
    log_result("/api/market/nifty100/top-movers", "GET", r.status_code, r.status_code in [200, 503], t)
else:
    log_result("/api/market/nifty100/top-movers", "GET", "ERROR", False, t)

# 18. Metrics Endpoint
r, t = test_endpoint(f"{BASE_URL}/metrics")
if r:
    log_result("/metrics", "GET", r.status_code, r.status_code == 200, t)
else:
    log_result("/metrics", "GET", "ERROR", False, t)

# ===================== SUMMARY =====================
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)

passed = sum(1 for r in results if r["success"])
failed = len(results) - passed
avg_time = sum(r["response_time_ms"] for r in results) / len(results)

print(f"Total Tests: {len(results)}")
print(f"Passed: {passed} ✅")
print(f"Failed: {failed} ❌")
print(f"Success Rate: {passed/len(results)*100:.1f}%")
print(f"Avg Response Time: {avg_time:.0f}ms")
print(f"Completed: {datetime.now().isoformat()}")

# Save results to JSON
with open("api_test_results.json", "w") as f:
    json.dump({
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "success_rate": round(passed/len(results)*100, 1),
            "avg_response_time_ms": round(avg_time, 2),
            "timestamp": datetime.now().isoformat()
        },
        "results": results
    }, f, indent=2)

print("\nResults saved to api_test_results.json")
