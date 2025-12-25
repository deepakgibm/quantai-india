"""
Debug AlphaPrime signals API
"""
import requests

# Get token
print("1. Getting auth token...")
login_response = requests.post(
    "http://localhost:8000/api/auth/login",
    json={"email": "demo@example.com", "password": "testpass123"}
)

if login_response.status_code != 200:
    print(f"Login failed: {login_response.text}")
    exit(1)

token = login_response.json()["access_token"]
print(f"✓ Token: {token[:30]}...")

# Test signals endpoint
print("\n2. Fetching alpha signals...")
signals_response = requests.get(
    "http://localhost:8000/api/v1/alpha-prime/signals?limit=10",
    headers={"Authorization": f"Bearer {token}"}
)

print(f"Status Code: {signals_response.status_code}")
print(f"Response: {signals_response.text[:500]}")

if signals_response.status_code == 200:
    signals = signals_response.json()
    print(f"\n✓ Retrieved {len(signals)} signals")
    if signals:
        print("\nFirst signal:")
        for key, value in signals[0].items():
            print(f"  {key}: {value}")
else:
    print(f"\n✗ Error: {signals_response.text}")
