import requests
import sys
import json

BASE_URL = "http://localhost:8000"
USER = {"email": "dthat53@gmail.com", "password": "admin1243"}

def main():
    # 1. Login
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/login", json=USER)
        if resp.status_code != 200:
            print(f"Login failed: {resp.status_code} {resp.text}")
            return
        token = resp.json()["access_token"]
        print("Login success.")
    except Exception as e:
        print(f"Login error: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Call Market Analysis (uses MarketAnalyst)
    print("Testing Market Analysis...")
    try:
        resp = requests.get(f"{BASE_URL}/api/ai/market-analysis", headers=headers, timeout=20)
        print(f"Market Analysis: {resp.status_code}")
        if resp.status_code == 200:
            print(json.dumps(resp.json(), indent=2)[:200] + "...")
        else:
            print(resp.text)
    except Exception as e:
        print(f"Market Analysis error: {e}")

    # 3. Call Trend Finder (uses ScannerRunner)
    print("Testing Trend Finder Scanner...")
    try:
        resp = requests.get(f"{BASE_URL}/api/ai/trend-finder", headers=headers, timeout=30)
        print(f"Trend Finder: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Found {len(data.get('stocks', []))} stocks")
            print(json.dumps(data, indent=2)[:200] + "...")
        else:
            print(resp.text)
    except Exception as e:
        print(f"Trend Finder error: {e}")

if __name__ == "__main__":
    main()
