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
    
    # Check Option Flow
    flow_url = f"{base_url}/api/option-flow/RELIANCE?bypass_cache=true"
    r_flow = requests.get(flow_url, headers=headers)
    if r_flow.status_code == 200:
        data = r_flow.json().get("data", {})
        strikes = data.get("strikes", [])
        print(f"Strikes count: {len(strikes)}")
        if strikes:
            # Print middle strike as sample (closest to ATM)
            mid = len(strikes) // 2
            print("Sample Strike:")
            print(json.dumps(strikes[mid], indent=2))

if __name__ == "__main__":
    main()
