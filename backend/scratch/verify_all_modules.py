import requests

def test_api():
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

    # 2. Test Volatility API (and verify ATR)
    vol_url = f"{base_url}/api/volatility/RELIANCE?lookback_days=30"
    print("\n[TEST] Volatility API (ATR verification): GET /api/volatility/RELIANCE")
    r = requests.get(vol_url, headers=headers)
    print(f"Status Code: {r.status_code}")
    if r.status_code == 200:
        res_json = r.json()
        print(f"Status: {res_json.get('status')}")
        print(f"Symbol: {res_json.get('symbol')}")
        print(f"ATR: {res_json.get('atr')}")
        print(f"IV Rank: {res_json.get('iv_rank')}")
        print(f"IV Percentile: {res_json.get('iv_percentile')}")
        time_series = res_json.get('time_series', [])
        if time_series:
            print(f"Sample Chart Point: {time_series[0]}")
    else:
        print(f"Failed: {r.text}")

    # 3. Test Option Flow API for multiple symbols
    test_symbols = ["RELIANCE", "NIFTY", "BANKNIFTY", "NIFTY 50", "NIFTY_50"]
    for sym in test_symbols:
        opt_url = f"{base_url}/api/option-flow/{sym}"
        print(f"\n[TEST] Option Flow API: GET /api/option-flow/{sym}")
        r = requests.get(opt_url, headers=headers)
        print(f"Status Code: {r.status_code}")
        if r.status_code == 200:
            res_json = r.json()
            print(f"Success: {res_json.get('success')}")
            if res_json.get('success'):
                data = res_json.get('data', {})
                print(f"PCR OI: {data.get('pcr_oi')}")
                print(f"Net Flow: {data.get('net_flow')}")
                print(f"Sentiment: {data.get('sentiment')}")
                print(f"Strikes Count: {len(data.get('strikes', []))}")
                print(f"Block Deals Count: {len(data.get('block_deals', []))}")
            else:
                error_info = res_json.get('error') or {}
                print(f"Error Message: {error_info.get('message')}")
        else:
            print(f"Failed: {r.text}")

    # 4. Test Heatmap API
    heatmap_url = f"{base_url}/api/heatmap?mode=performance"
    print("\n[TEST] Heatmap API: GET /api/heatmap?mode=performance")
    r = requests.get(heatmap_url, headers=headers)
    print(f"Status Code: {r.status_code}")
    if r.status_code == 200:
        res_json = r.json()
        print(f"Status: {res_json.get('status')}")
        print(f"Sectors Count: {len(res_json.get('sectors', []))}")
        if res_json.get('sectors'):
            sec = res_json.get('sectors')[0]
            print(f"Sample Sector: {sec.get('name')} (constituent count: {len(sec.get('stocks', []))})")
            if sec.get('stocks'):
                print(f"Sample Stock: {sec.get('stocks')[0]}")
    else:
        print(f"Failed: {r.text}")

if __name__ == "__main__":
    test_api()
