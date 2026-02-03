import requests
import time
import json

BASE_URL = "http://localhost:8000"

# Test user credentials (from QATestRunner)
TEST_USER = {
    "email": "dthat53@gmail.com",
    "password": "admin1243"
}

def authenticate():
    print("Authenticating...")
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/login", json=TEST_USER, timeout=5)
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            print("[AUTH] Success")
            return {"Authorization": f"Bearer {token}"}
        else:
            print(f"[AUTH] Failed: {resp.status_code} {resp.text}")
            return {}
    except Exception as e:
        print(f"[AUTH] Error: {e}")
        return {}

def test_endpoint(method, endpoint, expected_status=200, payload=None, headers=None):
    url = f"{BASE_URL}{endpoint}"
    print(f"Testing {method} {url}...")
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=5)
        else:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if resp.status_code == expected_status:
            print(f"[PASS]: {resp.status_code}")
            return True
        else:
            print(f"[FAIL]: Got {resp.status_code}, expected {expected_status}")
            print(f"Response: {resp.text}")
            return False
    except Exception as e:
        print(f"[ERROR]: {e}")
        return False

def verify_fixes():
    print("Waiting for server to be ready...")
    time.sleep(2)
    
    headers = authenticate()
    if not headers:
        print("Skipping tests due to auth failure")
        return

    # Verify Backtest Run
    print("\nTesting Backtest Run...")
    payload = {
        "symbol": "RELIANCE",
        "strategy": "MACrossover",
        "start_date": "2025-12-01",
        "end_date": "2026-02-01",
        "initial_capital": 100000,
        "params": {"fast_period": 10, "slow_period": 30, "ma_type": "EMA", "timeframe": "1D"}
    }
    test_endpoint("POST", "/api/v1/backtest/run", 200, payload, headers=headers)
    
    # Verify Walk-Forward
    print("\nTesting Walk-Forward...")
    wf_payload = {
        "symbols": ["RELIANCE"],
        "exchange": "NSE",
        "strategy_type": "RULE_BASED",
        "strategy_name": "ma_crossover",
        "timeframe": "1D",
        "trade_style": "SWING",
        "walk_forward": {
            "train_window": 100,
            "test_window": 20,
            "step_size": 20,
            "anchored": False
        },
        "capital": 100000,
        "ml_model": "NONE"
    }
    test_endpoint("POST", "/api/v1/walk-forward", 200, wf_payload, headers=headers)

if __name__ == "__main__":
    verify_fixes()
