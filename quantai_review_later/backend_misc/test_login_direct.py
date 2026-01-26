import requests

# Test login
url = "http://localhost:8000/api/auth/login"
data = {
    "email": "demo@example.com",
    "password": "demo123"
}

try:
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("\n✅ LOGIN SUCCESSFUL!")
        token = response.json().get('access_token')
        print(f"Token: {token[:50]}...")
    else:
        print("\n❌ LOGIN FAILED")
        
except Exception as e:
    print(f"Error: {e}")
