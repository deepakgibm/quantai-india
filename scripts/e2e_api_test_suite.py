import requests
import json
import time
import uuid

# Configuration
BASE_URL = "http://localhost:8000/api"
MARKET_DATA_URL = "http://localhost:8001"

def test_health():
    print("Testing Health Check...")
    # Main Backend Health
    response = requests.get(f"http://localhost:8000/api/health/")
    print(f"Backend Health: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    
    # Market Data Service Health (Skipped in current production config)
    # response = requests.get(f"{MARKET_DATA_URL}/health")
    # print(f"Market Data Service Health: {response.status_code}")
    # print(json.dumps(response.json(), indent=2))

def test_auth():
    print("\nTesting Authentication Flow...")
    email = f"test_{uuid.uuid4().hex[:6]}@example.com"
    password = "testpassword123"
    
    # 1. Signup
    username = f"user_{uuid.uuid4().hex[:6]}"
    signup_data = {
        "email": email,
        "username": username,
        "full_name": "Test User",
        "password": password
    }
    response = requests.post(f"{BASE_URL}/auth/signup", json=signup_data)
    print(f"Signup: {response.status_code}")
    
    if response.status_code == 200:
        # 2. Login
        login_data = {
            "email": email,
            "password": password
        }
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"Login: {response.status_code}")
        if response.status_code == 200:
            token = response.json()["access_token"]
            return token
    return None

def test_indicators(token):
    if not token: return
    print("\nTesting Indicators (Heatmap)...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/indicators/heatmap", headers=headers)
    print(f"Heatmap Indicators: {response.status_code}")
    if response.status_code == 200:
        print(f"Data Source: {response.json().get('source')}")
        print(f"Sector Count: {len(response.json().get('data', []))}")

def test_market_data(token):
    if not token: return
    print("\nTesting Market Data (LTP)...")
    headers = {"Authorization": f"Bearer {token}"}
    # Test LTP for Reliance via Upstox router
    response = requests.get(f"{BASE_URL}/upstox/market-quote/RELIANCE", headers=headers)
    print(f"Market LTP (RELIANCE): {response.status_code}")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error: {response.text}")

def test_ml_training(token):
    if not token: return
    print("\nTesting ML Training (Celery Dispatch)...")
    headers = {"Authorization": f"Bearer {token}"}
    # ML Training is in v1 with prefix /ml
    response = requests.post(f"{BASE_URL}/v1/ml/train/start?epochs=1", headers=headers)
    print(f"Training Dispatch: {response.status_code}")
    if response.status_code == 200:
        task_id = response.json().get("task_id")
        print(f"Task ID: {task_id}")
        # Wait and check status
        time.sleep(2)
        status_resp = requests.get(f"{BASE_URL}/v1/ml/train/status", headers=headers)
        print(f"Task Status: {status_resp.json().get('status')}")
    else:
        print(f"Error: {response.text}")

def test_analytics(token):
    if not token: return
    print("\nTesting Analytics (DuckDB)...")
    headers = {"Authorization": f"Bearer {token}"}
    query_data = {
        "sql": "SELECT count(*) as count FROM stock_candle",
        "params": {}
    }
    response = requests.post(f"{BASE_URL}/analytics/query", json=query_data, headers=headers)
    print(f"Analytics Query: {response.status_code}")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    test_health()
    token = test_auth()
    if token:
        test_indicators(token)
        test_market_data(token)
        test_ml_training(token)
        test_analytics(token)
    else:
        print("Auth failed, skipping protected endpoint tests.")
