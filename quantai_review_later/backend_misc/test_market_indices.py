"""Test the market-indices endpoint directly"""
import requests
import json

BASE_URL = "http://localhost:8000"

# First, login to get a token
print("Step 1: Login to get token...")
login_res = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={"email": "demo@example.com", "password": "demo123"},
    timeout=30
)

if login_res.status_code != 200:
    print(f"Login failed: {login_res.status_code} - {login_res.text}")
    exit(1)

token = login_res.json().get("access_token")
print(f"Got token: {token[:20]}...")

# Now fetch market indices
print("\nStep 2: Fetch market indices...")
indices_res = requests.get(
    f"{BASE_URL}/api/trading/market-indices",
    headers={"Authorization": f"Bearer {token}"},
    timeout=60  # Long timeout to get through rate limiting
)

print(f"Status: {indices_res.status_code}")
if indices_res.status_code == 200:
    data = indices_res.json()
    print("\nMarket Indices Response:")
    print(json.dumps(data, indent=2))
else:
    print(f"Error: {indices_res.text}")
