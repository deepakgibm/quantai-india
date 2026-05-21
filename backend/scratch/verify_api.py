import requests

def test_api():
    base_url = "http://localhost:8000"
    
    # 1. Login
    login_url = f"{base_url}/api/auth/login"
    login_payload = {
        "email": "test_auth@quantai.com",
        "password": "ValidPassword123!"
    }
    print(" Logging in...")
    r = requests.post(login_url, json=login_payload)
    if r.status_code != 200:
        print(f"Login failed: {r.status_code} - {r.text}")
        return
        
    token = r.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("Login successful.")

    # 2. Test Search Endpoint
    search_url = f"{base_url}/api/search/stocks?q=RELI"
    print("\n Testing Search API: GET /api/search/stocks?q=RELI")
    r = requests.get(search_url, headers=headers)
    print(f"Status Code: {r.status_code}")
    print(f"Response: {r.text[:500]}...")

    # 3. Test Volatility Endpoint (Valid Lookback)
    vol_url = f"{base_url}/api/volatility/RELIANCE?lookback_days=30"
    print("\n Testing Volatility API: GET /api/volatility/RELIANCE?lookback_days=30")
    r = requests.get(vol_url, headers=headers)
    print(f"Status Code: {r.status_code}")
    print(f"Response: {r.text[:500]}...")

    # 4. Test Volatility Endpoint (Invalid Lookback > 60)
    vol_url_invalid = f"{base_url}/api/volatility/RELIANCE?lookback_days=90"
    print("\n Testing Volatility API (Invalid Lookback > 60): GET /api/volatility/RELIANCE?lookback_days=90")
    r = requests.get(vol_url_invalid, headers=headers)
    print(f"Status Code: {r.status_code} (Expect 422)")
    print(f"Response: {r.text}")

    # 5. Test Option Flow Endpoint
    opt_url = f"{base_url}/api/option-flow/RELIANCE"
    print("\n Testing Option Flow API: GET /api/option-flow/RELIANCE")
    r = requests.get(opt_url, headers=headers)
    print(f"Status Code: {r.status_code}")
    print(f"Response: {r.text[:500]}...")

    # 6. Test Heatmap Endpoint
    heatmap_url = f"{base_url}/api/heatmap?mode=performance"
    print("\n Testing Heatmap API: GET /api/heatmap?mode=performance")
    r = requests.get(heatmap_url, headers=headers)
    print(f"Status Code: {r.status_code}")
    print(f"Response: {r.text[:500]}...")

if __name__ == "__main__":
    test_api()
