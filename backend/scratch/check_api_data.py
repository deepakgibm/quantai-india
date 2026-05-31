import requests
import json

def check_backend_api():
    base_url = "http://localhost:8000"
    
    # 1. Login to get auth token
    login_url = f"{base_url}/api/auth/login"
    login_payload = {
        "email": "test_auth@quantai.com",
        "password": "ValidPassword123!"
    }
    
    print("1. Logging in to QuantAI backend...")
    try:
        r = requests.post(login_url, json=login_payload)
        if r.status_code != 200:
            print(f"   Login failed: {r.status_code} - {r.text}")
            return
        token = r.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        print("   Login successful.")
    except Exception as e:
        print(f"   Login request failed: {e}")
        return

    # 2. Check Upstox connection status
    status_url = f"{base_url}/api/upstox/status"
    print(f"\n2. Checking broker status: GET {status_url}")
    try:
        r = requests.get(status_url, headers=headers)
        print(f"   Status Code: {r.status_code}")
        print(f"   Response: {json.dumps(r.json(), indent=2)}")
    except Exception as e:
        print(f"   Broker status request failed: {e}")

    # 3. Check Option Expiries
    exp_url = f"{base_url}/api/option-flow/RELIANCE/expiries?bypass_cache=true"
    print(f"\n3. Checking Option Expiries: GET {exp_url}")
    try:
        r = requests.get(exp_url, headers=headers)
        print(f"   Status Code: {r.status_code}")
        if r.status_code == 200:
            exp_data = r.json()
            print(f"   Source: {exp_data.get('source')}")
            print(f"   Expiries: {exp_data.get('data', {}).get('expiries')}")
        else:
            print(f"   Response: {r.text}")
    except Exception as e:
        print(f"   Expiries request failed: {e}")

    # 4. Check Option Flow metrics (using nearest expiry)
    flow_url = f"{base_url}/api/option-flow/RELIANCE?bypass_cache=true"
    print(f"\n4. Checking Option Flow (nearest expiry): GET {flow_url}")
    try:
        r = requests.get(flow_url, headers=headers)
        print(f"   Status Code: {r.status_code}")
        if r.status_code == 200:
            flow_data = r.json()
            print(f"   Success: {flow_data.get('success')}")
            print(f"   Source: {flow_data.get('source')}")
            data_payload = flow_data.get('data') or {}
            print(f"   Symbol: {data_payload.get('symbol')}")
            print(f"   Expiry: {data_payload.get('expiry')}")
            print(f"   Market Closed: {data_payload.get('market_closed')}")
            print(f"   Is Static Snapshot: {data_payload.get('is_static')}")
            print(f"   Call Turnover: {data_payload.get('total_call_premium')}")
            print(f"   Put Turnover: {data_payload.get('total_put_premium')}")
            print(f"   Strikes Count: {len(data_payload.get('strikes', []))}")
        else:
            print(f"   Response: {r.text}")
    except Exception as e:
        print(f"   Option flow request failed: {e}")

if __name__ == "__main__":
    check_backend_api()
