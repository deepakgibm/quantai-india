"""
Comprehensive E2E Testing for QuantAI India - Simplified Output
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000"

# Force UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def run_all_tests():
    print("=" * 60)
    print("QUANTAI INDIA - END TO END TESTING")
    print("=" * 60)
    
    results = []
    
    # Test 1: Health Check
    print("\n[TEST 1] Health Check")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        if r.status_code == 200 and r.json().get("status") == "healthy":
            print("  PASS: Backend is healthy")
            results.append(("Health Check", True))
        else:
            print(f"  FAIL: Status: {r.status_code}")
            results.append(("Health Check", False))
    except Exception as e:
        print(f"  FAIL: {e}")
        results.append(("Health Check", False))
    
    # Test 2: Market Indices
    print("\n[TEST 2] Market Indices API")
    try:
        r = requests.get(f"{BASE_URL}/api/trading/market-indices", timeout=60)
        if r.status_code == 200:
            data = r.json()
            print(f"  PASS: Retrieved {len(data)} indices")
            for idx in data:
                source = idx.get('source', 'unknown')
                print(f"    - {idx['name']}: {idx['value']} ({idx['percent']:.2f}%) [source: {source}]")
            results.append(("Market Indices", True))
        else:
            print(f"  FAIL: Status: {r.status_code}")
            results.append(("Market Indices", False))
    except Exception as e:
        print(f"  FAIL: {e}")
        results.append(("Market Indices", False))
    
    # Test 3: Login
    print("\n[TEST 3] User Login")
    token = None
    try:
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "demo@example.com", "password": "demo123"},
            timeout=10
        )
        if r.status_code == 200:
            token = r.json().get("access_token")
            print(f"  PASS: Login successful")
            results.append(("Login", True))
        else:
            print(f"  FAIL: Status: {r.status_code} - {r.text[:100]}")
            results.append(("Login", False))
    except Exception as e:
        print(f"  FAIL: {e}")
        results.append(("Login", False))
    
    if not token:
        print("\n[SKIP] Remaining tests require authentication")
        print_summary(results)
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 4: User Profile
    print("\n[TEST 4] User Profile")
    try:
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=headers, timeout=10)
        if r.status_code == 200:
            user = r.json()
            print(f"  PASS: User: {user.get('email', 'N/A')}")
            results.append(("User Profile", True))
        else:
            print(f"  FAIL: Status: {r.status_code}")
            results.append(("User Profile", False))
    except Exception as e:
        print(f"  FAIL: {e}")
        results.append(("User Profile", False))
    
    # Test 5: Dashboard Stats
    print("\n[TEST 5] Dashboard Stats")
    try:
        r = requests.get(f"{BASE_URL}/api/trading/dashboard", headers=headers, timeout=10)
        if r.status_code == 200:
            print(f"  PASS: Dashboard data retrieved")
            results.append(("Dashboard Stats", True))
        else:
            print(f"  FAIL: Status: {r.status_code}")
            results.append(("Dashboard Stats", False))
    except Exception as e:
        print(f"  FAIL: {e}")
        results.append(("Dashboard Stats", False))
    
    # Test 6: Gainers/Losers
    print("\n[TEST 6] Gainers/Losers")
    try:
        r = requests.get(f"{BASE_URL}/api/trading/gainers-losers", headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict):
                gainers = data.get("gainers", [])
                losers = data.get("losers", [])
                print(f"  PASS: {len(gainers)} gainers, {len(losers)} losers")
            else:
                print(f"  PASS: Data retrieved")
            results.append(("Gainers/Losers", True))
        else:
            print(f"  FAIL: Status: {r.status_code}")
            results.append(("Gainers/Losers", False))
    except Exception as e:
        print(f"  FAIL: {e}")
        results.append(("Gainers/Losers", False))
    
    # Test 7: Quant Symbols
    print("\n[TEST 7] Quant Symbols")
    try:
        r = requests.get(f"{BASE_URL}/api/quant/symbols", headers=headers, timeout=10)
        if r.status_code == 200:
            symbols = r.json()
            print(f"  PASS: {len(symbols)} symbols available")
            results.append(("Quant Symbols", True))
        else:
            print(f"  WARN: Status: {r.status_code}")
            results.append(("Quant Symbols", False))
    except Exception as e:
        print(f"  WARN: {e}")
        results.append(("Quant Symbols", False))
    
    # Test 8: Frontend
    print("\n[TEST 8] Frontend Availability")
    try:
        r = requests.get("http://localhost:3000", timeout=5)
        if r.status_code == 200:
            print("  PASS: Frontend is accessible")
            results.append(("Frontend", True))
        else:
            print(f"  WARN: Status: {r.status_code}")
            results.append(("Frontend", False))
    except Exception as e:
        print(f"  WARN: Frontend not running - {type(e).__name__}")
        results.append(("Frontend", False))
    
    print_summary(results)


def print_summary(results):
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, status in results if status)
    total = len(results)
    
    for name, status in results:
        icon = "PASS" if status else "FAIL"
        print(f"  [{icon}] {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({100*passed//total if total else 0}%)")
    print("=" * 60)
    
    if passed == total:
        print("\nALL TESTS PASSED! QuantAI is fully functional!")
    elif passed >= total * 0.7:
        print("\nMost tests passed. Some optional features may need attention.")
    else:
        print("\nSome tests failed. Please check the errors above.")


if __name__ == "__main__":
    run_all_tests()
