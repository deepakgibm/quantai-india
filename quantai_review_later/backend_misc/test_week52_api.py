"""Test the week52-breakouts API endpoint"""
import requests
import json

BASE_URL = "http://localhost:8000"

# Login first
print("Step 1: Login...")
login_res = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={"email": "demo@example.com", "password": "demo123"},
    timeout=30
)

if login_res.status_code != 200:
    print(f"Login failed: {login_res.status_code}")
    exit(1)

token = login_res.json().get("access_token")
print(f"Got token: {token[:20]}...")

# Test week52-breakouts endpoint
print("\nStep 2: Fetching 52-week breakouts...")
res = requests.get(
    f"{BASE_URL}/api/scanner/week52-breakouts",
    headers={"Authorization": f"Bearer {token}"},
    timeout=120
)

print(f"Status: {res.status_code}")
if res.status_code == 200:
    data = res.json()
    print(f"\nResponse Summary:")
    print(f"  Status: {data.get('status')}")
    print(f"  High Breakouts: {len(data.get('high_breakouts', []))}")
    print(f"  Low Breakdowns: {len(data.get('low_breakdowns', []))}")
    
    print(f"\n--- First 3 High Breakouts ---")
    for stock in data.get('high_breakouts', [])[:3]:
        print(f"  {stock['symbol']}: LTP=₹{stock['ltp']}, 52WH=₹{stock['high_52w']}, Breakout={stock['breakout_pct']}%")
    
    print(f"\n--- First 3 Low Breakdowns ---")
    for stock in data.get('low_breakdowns', [])[:3]:
        print(f"  {stock['symbol']}: LTP=₹{stock['ltp']}, 52WL=₹{stock['low_52w']}, Breakdown={stock['breakout_pct']}%")
else:
    print(f"Error: {res.text}")
