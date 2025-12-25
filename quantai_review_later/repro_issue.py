
import requests
import json

BASE_URL = "http://localhost:8000"

def test_repro():
    # 1. Login to get token
    print("Logging in...")
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "integration_test@example.com", "password": "testpass123"})
    if resp.status_code != 200:
        print("Login failed")
        return
    token = resp.json()['access_token']
    
    headers = {"Authorization": f"Bearer {token}"}
    
    prompt = "Research top 5 stocks for this week"
    
    print(f"\nSending prompt to /api/ai/prompt: '{prompt}'")
    try:
        resp = requests.post(f"{BASE_URL}/api/ai/prompt", json={"prompt": prompt}, headers=headers)
        print(f"Status: {resp.status_code}")
        print("Response body:")
        print(resp.text)
    except Exception as e:
        print(f"Error: {e}")

    print(f"\nSending prompt to /api/agentic-bot/analyze: '{prompt}'")
    try:
        resp = requests.post(f"{BASE_URL}/api/agentic-bot/analyze", json={"prompt": prompt}, headers=headers)
        print(f"Status: {resp.status_code}")
        print("Response body:")
        print(resp.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_repro()
