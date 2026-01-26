"""
Create demo user for testing
"""
import requests

# Create demo user
signup_data = {
    "email": "demo@example.com",
    "username": "demo",
    "full_name": "Demo User",
    "password": "testpass123"
}

print("Creating demo user...")
try:
    response = requests.post(
        "http://localhost:8000/api/auth/signup",
        json=signup_data,
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 200:
        print("✅ Demo user created successfully!")
        print(f"Response: {response.json()}")
    else:
        print(f"⚠️  Status: {response.status_code}")
        print(f"Response: {response.text}")
        if response.status_code == 400 and "already registered" in response.text.lower():
            print("✅ Demo user already exists - you can login!")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Test login
print("\nTesting login...")
try:
    login_data = {
        "email": "demo@example.com",
        "password": "testpass123"
    }
    
    response = requests.post(
        "http://localhost:8000/api/auth/login",
        json=login_data,
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 200:
        print("✅ Login successful!")
        data = response.json()
        print(f"Token: {data.get('access_token')[:50]}...")
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Login error: {e}")
