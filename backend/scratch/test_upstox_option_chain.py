import requests
import json

def test_direct():
    token = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI3NzYyMjgiLCJqdGkiOiI2OWZiNmY2ZDA3YzlmYTFmZjhkYTRhZGUiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlzRXh0ZW5kZWQiOnRydWUsImlhdCI6MTc3ODA4NTc0MSwiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxODA5NjQwODAwfQ.WuaunJG4GqlEfCV5lCt4PrVNDZs1yFqAeO0ycfencjo"
    api_key = "7498f0fe-7ae7-4fb4-b230-13f83ccea251"
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Api-Key": api_key
    }
    
    # 1. Reliance Instrument Key
    # From instrument_master we know RELIANCE is "NSE_EQ|INE002A01018"
    inst_key = "NSE_EQ|INE002A01018"
    
    # Expiry
    expiry = "2026-05-28"
    
    url = "https://api.upstox.com/v2/option/chain"
    
    # Test A: with expiry_date
    params_a = {"instrument_key": inst_key, "expiry_date": expiry}
    print(f"Calling Upstox Option Chain WITH expiry_date: {expiry}")
    r_a = requests.get(url, headers=headers, params=params_a)
    print(f"Response Code: {r_a.status_code}")
    print(f"Response: {r_a.text[:1000]}")
    
    # Test B: without expiry_date
    params_b = {"instrument_key": inst_key}
    print(f"\nCalling Upstox Option Chain WITHOUT expiry_date")
    r_b = requests.get(url, headers=headers, params=params_b)
    print(f"Response Code: {r_b.status_code}")
    print(f"Response: {r_b.text[:1000]}")

if __name__ == "__main__":
    test_direct()
