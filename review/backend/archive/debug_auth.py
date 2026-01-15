
import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def debug_auth():
    print("Logging in...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/token",
            data={"username": "dthat@gmail.com", "password": "admin123"},
            timeout=10
        )
        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            return
            
        token = response.json().get("access_token")
        print(f"Token received: {token[:20]}...")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        print("\nRequesting /api/auth/me...")
        me_resp = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        print(f"Response: {me_resp.status_code}")
        print(f"Body: {me_resp.text}")
        
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    debug_auth()
