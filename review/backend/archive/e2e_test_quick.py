"""
E2E Testing Script for QuantAI Backend
"""
import requests

BASE_URL = "http://localhost:8000"

def run_tests():
    print("=" * 60)
    print("QUANTAI BACKEND E2E TESTING")
    print("=" * 60)
    
    results = []
    
    # Test 1: Health Check
    print("\n[TEST 1] Health Check")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        if r.status_code == 200:
            print(f"  PASS: Status {r.status_code}")
            results.append(("Health Check", True))
        else:
            print(f"  FAIL: Status {r.status_code}")
            results.append(("Health Check", False))
    except Exception as e:
        print(f"  FAIL: {e}")
        results.append(("Health Check", False))
    
    # Test 2: Root
    print("\n[TEST 2] Root Endpoint")
    try:
        r = requests.get(f"{BASE_URL}/", timeout=5)
        if r.status_code == 200:
            print(f"  PASS: {r.json()}")
            results.append(("Root", True))
        else:
            print(f"  FAIL: Status {r.status_code}")
            results.append(("Root", False))
    except Exception as e:
        print(f"  FAIL: {e}")
        results.append(("Root", False))
    
    # Test 3: Login
    print("\n[TEST 3] User Login")
    token = None
    try:
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "demo@example.com", "password": "demo123"}, timeout=10)
        if r.status_code == 200:
            token = r.json().get("access_token")
            print(f"  PASS: Got token")
            results.append(("Login", True))
        else:
            print(f"  INFO: Status {r.status_code} (demo user may not exist)")
            results.append(("Login", False))
    except Exception as e:
        print(f"  FAIL: {e}")
        results.append(("Login", False))
    
    # Test 4: AI Sentiment (new endpoint)
    print("\n[TEST 4] AI Sentiment Proxy")
    try:
        r = requests.get(f"{BASE_URL}/api/ai/sentiment?symbol=RELIANCE", timeout=30)
        if r.status_code == 200:
            data = r.json()
            sentiment = data.get("sentiment", "N/A")
            summary = data.get("summary", "N/A")[:50] if data.get("summary") else "N/A"
            print(f"  PASS: {sentiment} - {summary}...")
            results.append(("AI Sentiment", True))
        else:
            print(f"  INFO: Status {r.status_code}")
            results.append(("AI Sentiment", False))
    except Exception as e:
        print(f"  FAIL: {e}")
        results.append(("AI Sentiment", False))
    
    # Test 5: Market Indices
    print("\n[TEST 5] Market Indices")
    try:
        r = requests.get(f"{BASE_URL}/api/trading/market-indices", timeout=60)
        if r.status_code == 200:
            print(f"  PASS: Got {len(r.json())} indices")
            results.append(("Market Indices", True))
        elif r.status_code == 401:
            print(f"  INFO: Requires auth (401)")
            results.append(("Market Indices", False))
        else:
            print(f"  INFO: Status {r.status_code}")
            results.append(("Market Indices", False))
    except Exception as e:
        print(f"  FAIL: {e}")
        results.append(("Market Indices", False))
    
    # Test 6: Gainers/Losers
    print("\n[TEST 6] Gainers/Losers")
    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        r = requests.get(f"{BASE_URL}/api/trading/gainers-losers", headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            print(f"  PASS: Data retrieved")
            results.append(("Gainers/Losers", True))
        elif r.status_code == 401:
            print(f"  INFO: Requires auth (401)")
            results.append(("Gainers/Losers", False))
        else:
            print(f"  INFO: Status {r.status_code}")
            results.append(("Gainers/Losers", False))
    except Exception as e:
        print(f"  FAIL: {e}")
        results.append(("Gainers/Losers", False))
    
    # Test 7: Quant Symbols
    print("\n[TEST 7] Quant Symbols")
    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        r = requests.get(f"{BASE_URL}/api/quant/symbols", headers=headers, timeout=10)
        if r.status_code == 200:
            symbols = r.json()
            print(f"  PASS: {len(symbols)} symbols available")
            results.append(("Quant Symbols", True))
        else:
            print(f"  INFO: Status {r.status_code}")
            results.append(("Quant Symbols", False))
    except Exception as e:
        print(f"  FAIL: {e}")
        results.append(("Quant Symbols", False))
    
    # Summary
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

if __name__ == "__main__":
    run_tests()
