import requests
import json

BASE_URL = "http://localhost:8000"

def test_dashboard_apis():
    print("Testing Dashboard APIs...")
    
    # 1. Login
    try:
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "demo123"
        })
        if login_res.status_code != 200:
            print(f"FAILED: Login failed with {login_res.status_code}")
            return
        
        token = login_res.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Logged in successfully.")
        
        # 2. Get User
        res = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        print(f"User API: {res.status_code} - {res.json().get('username')}")
        
        # 3. Get Dashboard Stats
        res = requests.get(f"{BASE_URL}/api/trading/dashboard", headers=headers)
        print(f"Dashboard Stats: {res.status_code}")
        if res.status_code == 200:
            print(f"   Data: {json.dumps(res.json(), indent=2)}")
            
        # 4. Get Market Indices
        res = requests.get(f"{BASE_URL}/api/trading/market-indices", headers=headers)
        print(f"Market Indices: {res.status_code}")
        
        # 5. Get Heatmap
        res = requests.get(f"{BASE_URL}/api/market/heatmap", headers=headers)
        print(f"Sector Heatmap: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            print(f"   Status: {data.get('status')}")
            print(f"   Verdict: {data.get('market_outlook', {}).get('verdict')}")
            
        # 6. Get Gainers/Losers
        res = requests.get(f"{BASE_URL}/api/trading/gainers-losers", headers=headers)
        print(f"Gainers/Losers: {res.status_code}")

    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    test_dashboard_apis()
