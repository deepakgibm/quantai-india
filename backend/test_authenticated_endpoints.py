import requests
import json
import time
from datetime import datetime
from typing import Dict

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

CREDENTIALS = {
    "email": "dthat53@gmail.com",
    "password": "admin1243"
}

# Endpoints that required auth in previous run
AUTH_REQUIRED_ENDPOINTS = [
    ("AI Strategies", "Get AI Strategies", "GET", "/api/ai/strategies"),
    ("Scanner", "Get Strategies", "GET", "/api/scanner/strategies"),
    ("Scanner", "Get Indices", "GET", "/api/scanner/indices"),
    ("Scanner", "Get Timeframes", "GET", "/api/scanner/timeframes"),
    ("Scanner", "Presets", "GET", "/api/scanner/presets"),
    ("Scanner", "Momentum Data", "GET", "/api/scanner/momentum"),
    ("Scanner", "Reversal Data", "GET", "/api/scanner/reversal"),
    ("Scanner", "TrendFinder Data", "GET", "/api/scanner/trendfinder"),
    ("Heatmap", "Get Sectors", "GET", "/api/heatmap/sectors"),
    ("Upstox", "User Profile", "GET", "/api/upstox/user-profile"),
    ("Upstox", "Portfolio", "GET", "/api/upstox/portfolio"),
    ("Orders", "Get Orders", "GET", "/api/orders/"),
    ("Algorithms", "Get Algorithms", "GET", "/api/algorithms/"),
    ("Risk Management", "Get Risk Settings", "GET", "/api/risk/"),
    ("Settings", "Get Settings", "GET", "/api/settings/"),
]

def get_token():
    print(f"Logging in as {CREDENTIALS['email']}...")
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS, timeout=10)
        if response.status_code == 200:
            token = response.json().get("access_token")
            print("Login successful.")
            return token
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Login error: {e}")
        return None

def test_endpoint(category: str, name: str, method: str, path: str, token: str) -> Dict:
    url = f"{BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {token}"}
    start_time = time.time()
    
    result = {
        "category": category,
        "name": name,
        "method": method,
        "path": path,
        "status": "UNKNOWN",
        "status_code": None,
        "response_time_ms": None,
        "error": None
    }
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=TIMEOUT)
        elif method == "POST":
            response = requests.post(url, headers=headers, json={}, timeout=TIMEOUT)
        else:
            response = requests.request(method, url, headers=headers, timeout=TIMEOUT)
            
        elapsed = (time.time() - start_time) * 1000
        result["status_code"] = response.status_code
        result["response_time_ms"] = round(elapsed, 2)
        
        if response.status_code < 400:
            result["status"] = "PASS"
        else:
            result["status"] = "FAIL"
            try:
                result["error"] = response.json()
            except:
                result["error"] = response.text[:100]
                
    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)
        
    return result

def run_tests():
    token = get_token()
    if not token:
        print("Could not obtain token. Aborting.")
        return

    print(f"\n{'='*60}")
    print(f"QuantAI Authenticated API Tests")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    results = []
    
    for category, name, method, path in AUTH_REQUIRED_ENDPOINTS:
        result = test_endpoint(category, name, method, path, token)
        results.append(result)
        
        status_icon = "✓" if result["status"] == "PASS" else "✗"
        print(f"  {status_icon} [{category}] {name}: {result['status']} ({result['status_code']}) - {result.get('response_time_ms', 'N/A')}ms")
        if result["status"] != "PASS":
            print(f"    Error: {result['error']}")
        
    # Generate summary report
    passed = len([r for r in results if r["status"] == "PASS"])
    total = len(results)
    
    print(f"\n{'='*60}")
    print(f"Summary: {passed}/{total} Passed")
    print(f"{'='*60}")
    
    with open("authenticated_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_tests()
