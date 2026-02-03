
import requests
import sys

def verify_market_analysis():
    # 1. Login
    login_url = "http://localhost:8000/api/auth/login"
    payload = {
        "email": "dthat53@gmail.com",
        "password": "admin1243"
    }
    try:
        resp = requests.post(login_url, json=payload)
        resp.raise_for_status()
        token = resp.json()["access_token"]
        print("Login Check: Success")
    except Exception as e:
        print(f"Login failed: {e}")
        sys.exit(1)

    # 2. Call Market Analysis
    url = "http://localhost:8000/api/ai/market-analysis"
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"Testing {url}...")
    try:
        resp = requests.get(url, headers=headers)
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.text}")
        
        if resp.status_code == 200:
            print("Verification Check: Success (200 OK)")
            # verify schema keys
            data = resp.json()
            required_keys = ["status", "analysis", "sentiment", "trend", "top_sectors", "stocks_to_watch", "timestamp"]
            missing = [k for k in required_keys if k not in data]
            if missing:
                print(f"Schema Check: Failed (Missing keys: {missing})")
                sys.exit(1)
            else:
                print("Schema Check: Success")
        else:
            print("Verification Check: Failed (Not 200)")
            sys.exit(1)
            
    except Exception as e:
        print(f"Exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_market_analysis()
