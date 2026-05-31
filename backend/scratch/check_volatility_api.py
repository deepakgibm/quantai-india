import requests
import json

def main():
    base_url = "http://localhost:8000"
    
    # Login
    login_url = f"{base_url}/api/auth/login"
    login_payload = {
        "email": "test_auth@quantai.com",
        "password": "ValidPassword123!"
    }
    
    r = requests.post(login_url, json=login_payload)
    token = r.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Check Volatility
    vol_url = f"{base_url}/api/volatility/RELIANCE"
    print(f"Calling GET {vol_url}")
    r_vol = requests.get(vol_url, headers=headers)
    print(f"Status Code: {r_vol.status_code}")
    if r_vol.status_code == 200:
        print(json.dumps(r_vol.json(), indent=2))

if __name__ == "__main__":
    main()
