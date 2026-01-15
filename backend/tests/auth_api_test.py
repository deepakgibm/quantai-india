import requests
import json
import uuid

BASE_URL = "http://localhost:8000"
TEST_USER_EMAIL = f"testuser_{uuid.uuid4().hex[:6]}@example.com"
TEST_USER_PASSWORD = "TestPassword123!"
TEST_USERNAME = f"tester_{uuid.uuid4().hex[:6]}"

def test_api():
    print(f"--- Starting API Testing for {TEST_USER_EMAIL} ---")

    # 1. Signup
    print("\n[1] Registering new user...")
    signup_payload = {
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD,
        "username": TEST_USERNAME,
        "full_name": "API Tester"
    }
    response = requests.post(f"{BASE_URL}/api/auth/signup", json=signup_payload)
    if response.status_code == 200:
        print(f"SUCCESS: User {TEST_USER_EMAIL} created.")
    else:
        print(f"FAILED: Signup returned {response.status_code} - {response.text}")
        return

    # 2. Login
    print("\n[2] Logging in...")
    login_payload = {
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    }
    response = requests.post(f"{BASE_URL}/api/auth/login", json=login_payload)
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get("access_token")
        print("SUCCESS: Login successful. Token obtained.")
    else:
        print(f"FAILED: Login returned {response.status_code} - {response.text}")
        return

    headers = {"Authorization": f"Bearer {access_token}"}

    # 3. Test Me
    print("\n[3] Testing /api/auth/me...")
    response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    if response.status_code == 200:
        print(f"SUCCESS: Profile retrieved: {response.json().get('email')}")
    else:
        print(f"FAILED: /me returned {response.status_code}")

    # 4. Test Orders (Should be empty but valid)
    print("\n[4] Testing /api/orders/...")
    response = requests.get(f"{BASE_URL}/api/orders/", headers=headers)
    if response.status_code == 200:
        print(f"SUCCESS: Orders retrieved (Count: {len(response.json())})")
    else:
        print(f"FAILED: /orders returned {response.status_code} - {response.text}")

    # 5. Test Risk Settings
    print("\n[5] Testing /api/risk/...")
    response = requests.get(f"{BASE_URL}/api/risk/", headers=headers)
    if response.status_code == 200:
        risk_data = response.json()
        print(f"SUCCESS: Risk settings retrieved (Capital: {risk_data.get('max_capital')})")
    else:
        print(f"FAILED: /risk returned {response.status_code} - {response.text}")

    # 6. Test AI Strategy
    print("\n[6] Testing /api/ai/top5-picks...")
    response = requests.get(f"{BASE_URL}/api/ai/top5-picks", headers=headers)
    if response.status_code == 200:
        print(f"SUCCESS: AI Top Picks retrieved (Count: {len(response.json().get('stocks', []))})")
    else:
        print(f"FAILED: /top5-picks returned {response.status_code} - {response.text}")

    # 7. Test Scanners
    print("\n[7] Testing /api/scanner/momentum...")
    response = requests.get(f"{BASE_URL}/api/scanner/momentum", headers=headers)
    if response.status_code == 200:
        print(f"SUCCESS: Momentum scanner retrieved (Count: {len(response.json().get('gainers', []))})")
    else:
        print(f"FAILED: /momentum returned {response.status_code} - {response.text}")

    # 8. Test Trading Stats
    print("\n[8] Testing /api/trading/stats...")
    response = requests.get(f"{BASE_URL}/api/trading/stats", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"SUCCESS: Stats retrieved. Capital: {data.get('total_capital')}, Trades: {data.get('total_trades')}")
    else:
        print(f"FAILED: /stats returned {response.status_code} - {response.text}")

    # 9. Test Top Gainers
    print("\n[9] Testing /api/trading/top-gainers...")
    response = requests.get(f"{BASE_URL}/api/trading/top-gainers", headers=headers)
    if response.status_code == 200:
        gainers = response.json()
        print(f"SUCCESS: Top Gainers retrieved (Count: {len(gainers)})")
        if gainers:
            print(f"Sample: {gainers[0].get('symbol')} (+{gainers[0].get('change')}%)")
    else:
        print(f"FAILED: /top-gainers returned {response.status_code} - {response.text}")

    # 10. Test Gainers-Losers
    print("\n[10] Testing /api/trading/gainers-losers...")
    response = requests.get(f"{BASE_URL}/api/trading/gainers-losers", headers=headers)
    if response.status_code == 200:
        print(f"SUCCESS: Gainers-Losers retrieved (Count: {len(response.json())})")
    else:
        print(f"FAILED: /gainers-losers returned {response.status_code} - {response.text}")

    print("\n--- API Testing Completed ---")

if __name__ == "__main__":
    test_api()
