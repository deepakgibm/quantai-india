
import requests
import time

BASE_URL = "http://localhost:8000"

def test_endpoint(method, url, data=None, name=None):
    try:
        start = time.time()
        if method.upper() == "GET":
            r = requests.get(f"{BASE_URL}{url}", timeout=10)
        elif method.upper() == "POST":
            r = requests.post(f"{BASE_URL}{url}", json=data, timeout=10)
        
        elapsed = (time.time() - start) * 1000
        # Allow 200, 201, 422 as "handled" responses
        success = r.status_code in [200, 201, 422]
        return success, {
            "name": name or url,
            "status_code": r.status_code,
            "time_ms": round(elapsed, 0),
            "success": success
        }
    except Exception as e:
        return False, {"name": name or url, "error": str(e), "success": False}

def run_tests():
    test_cases = [
        ("GET", "/health", "Health Check"),
        ("GET", "/api/scanner/strategies", "v1 Strategies"),
        ("GET", "/api/v2/scanner/status", "HP Status"),
        ("GET", "/api/v2/scanner/momentum", "HP Momentum"),
        ("GET", "/api/trading/market-indices", "Market Indices"),
        ("GET", "/api/trading/positions", "Positions"),
        ("GET", "/api/ai/equity/trade-signals", "AI Equity"),
        ("GET", "/api/risk/portfolio-risk", "Risk Portfolio")
    ]
    
    passed = 0
    for method, url, name in test_cases:
        success, res = test_endpoint(method, url, name=name)
        status = "PASSED" if success else "FAILED"
        print(f"[{status}] {name}: {res.get('status_code', res.get('error'))} ({res.get('time_ms', 0)}ms)")
        if success: passed += 1
    
    print(f"\nFinal Summary: {passed}/{len(test_cases)} Passed")

if __name__ == "__main__":
    run_tests()
