"""
Test login endpoint
"""
import requests

print("Testing login endpoint...")

# Test health check first
try:
    health = requests.get("http://localhost:8000/health")
    print(f"✓ Backend health check: {health.json()}")
except Exception as e:
    print(f"✗ Backend health check failed: {e}")
    exit(1)

# Test login
try:
    response = requests.post(
        "http://localhost:8000/api/auth/login",
        json={
            "email": "demo@example.com",
            "password": "testpass123"
        }
    )
    
    print(f"\nLogin Response Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Login successful!")
        print(f"  Access Token: {data.get('access_token', 'N/A')[:50]}...")
    else:
        print(f"✗ Login failed!")
        print(f"  Response: {response.text}")
        
except Exception as e:
    print(f"✗ Login request failed: {e}")
