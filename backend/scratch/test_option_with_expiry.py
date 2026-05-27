import requests

def test_option_with_expiry():
    base_url = "http://localhost:8000"
    
    # 1. Login
    login_url = f"{base_url}/api/auth/login"
    login_payload = {
        "email": "test_auth@quantai.com",
        "password": "ValidPassword123!"
    }
    print("Logging in...")
    r = requests.post(login_url, json=login_payload)
    if r.status_code != 200:
        print(f"Login failed: {r.status_code} - {r.text}")
        return
        
    token = r.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("Login successful.")

    # 2. Get Expiries
    for symbol in ["RELIANCE", "NIFTY"]:
        exp_url = f"{base_url}/api/option-flow/{symbol}/expiries"
        print(f"\n[TEST] Get Expiries: GET {exp_url}")
        r = requests.get(exp_url, headers=headers)
        print(f"Status Code: {r.status_code}")
        if r.status_code == 200:
            res = r.json()
            data = res.get("data", {})
            expiries = data.get("expiries", [])
            print(f"Expiries for {symbol}: {expiries}")
            if expiries:
                # 3. Test Option Flow with first expiry
                first_expiry = expiries[0]
                flow_url = f"{base_url}/api/option-flow/{symbol}?expiry={first_expiry}"
                print(f"[TEST] Option Flow with expiry: GET {flow_url}")
                r_flow = requests.get(flow_url, headers=headers)
                print(f"Status Code: {r_flow.status_code}")
                print(f"Response: {r_flow.text[:1000]}")
            else:
                print("No expiries found.")
        else:
            print(f"Failed to get expiries: {r.text}")

if __name__ == "__main__":
    test_option_with_expiry()
