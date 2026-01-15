import requests
import json

BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/api/auth/login"

credentials = {
    "email": "dthat53@gmail.com",
    "password": "admin1243"
}

print(f"Testing Login at {LOGIN_URL}")
print(f"Payload: {json.dumps(credentials)}")

try:
    response = requests.post(LOGIN_URL, json=credentials, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {response.headers}")
    print(f"Response Body: {response.text}")
    
    if response.status_code == 200:
        token_data = response.json()
        print("\nSUCCESS! Token obtained.")
        print(f"Token: {token_data.get('access_token')[:20]}...")
except Exception as e:
    print(f"Error: {e}")
