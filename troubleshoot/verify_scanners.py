
import requests
import json
import time

BASE_URL = "http://localhost:8000"
SCANNERS = [
    "/api/ai/trend-finder",
    "/api/ai/breakout-detector",
    "/api/ai/momentum",
    "/api/ai/mean-reversion",
    "/api/ai/gap",
    "/api/ai/vwap",
    "/api/ai/sr-bounce"
]

def login():
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "dthat53@gmail.com", "password": "admin1243"})
        if resp.status_code == 200:
            return resp.json()["access_token"]
        print(f"Login failed: {resp.text}")
    except Exception as e:
        print(f"Login error: {e}")
    return None

def check_scanner(token, endpoint):
    headers = {"Authorization": f"Bearer {token}"}
    print(f"\nTesting {endpoint}...")
    try:
        t0 = time.time()
        resp = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
        elapsed = time.time() - t0
        
        status = resp.status_code
        try:
            data = resp.json()
        except:
            data = resp.text[:200]
            
        print(f"Status: {status} (in {elapsed:.2f}s)")
        
        if status == 200:
            print(f"Result Count: {data.get('count', 'N/A')}")
            # print(json.dumps(data, indent=2))
        else:
            print(f"ERROR: {data}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    token = login()
    if token:
        for scanner in SCANNERS:
            check_scanner(token, scanner)
