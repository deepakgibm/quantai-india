
import requests
import json
import sys

def test_login():
    url = "http://localhost:8000/api/auth/login"
    payload = {
        "email": "dthat53@gmail.com",
        "password": "admin1243"
    }
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"Testing {url} with payload {payload}")
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code != 200:
            print("Login Failed!")
            sys.exit(1)
        else:
            print("Login Successful!")
            
    except Exception as e:
        print(f"Exception: {e}")
        sys.exit(1)

def test_health():
    url = "http://localhost:8000/health"
    print(f"Testing {url}")
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_health()
    test_login()
