
import requests

BASE_URL = "http://localhost:8000"

def test_login():
    url = f"{BASE_URL}/api/auth/login"
    payload = {"email": "dthat@gmail.com", "password": "admin123"}
    print(f"Testing POST {url} with {payload}")
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Body: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_login()
