"""
Check Upstox Token Validity and Test API Endpoints
"""
import os
import sys
from datetime import datetime
import base64
import json
import requests

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def decode_jwt_expiry(token: str) -> dict:
    """Decode a JWT token to check its expiry without verification."""
    try:
        # Split the JWT into its parts
        parts = token.split('.')
        if len(parts) != 3:
            return {"error": "Invalid JWT format"}
        
        # Decode the payload (second part)
        payload = parts[1]
        # Add padding if needed
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        
        decoded = base64.urlsafe_b64decode(payload)
        payload_data = json.loads(decoded)
        
        return payload_data
    except Exception as e:
        return {"error": str(e)}


def check_token_expiry():
    """Check if the Upstox access token is expired."""
    print("\n" + "=" * 60)
    print("[TOKEN] UPSTOX TOKEN VALIDITY CHECK")
    print("=" * 60)
    
    token = os.getenv("UPSTOX_ACCESS_TOKEN", "")
    
    if not token:
        print("[FAIL] No UPSTOX_ACCESS_TOKEN found in .env file!")
        return False, None
    
    print(f"\n[INFO] Token (first 50 chars): {token[:50]}...")
    
    # Decode JWT to check expiry
    payload = decode_jwt_expiry(token)
    
    if "error" in payload:
        print(f"[WARN] Could not decode token: {payload['error']}")
        return None, payload
    
    print(f"\n[INFO] Token Payload:")
    print(f"   Subject (sub): {payload.get('sub', 'N/A')}")
    print(f"   Token ID (jti): {payload.get('jti', 'N/A')}")
    print(f"   Issuer (iss): {payload.get('iss', 'N/A')}")
    
    # Check expiry
    exp_timestamp = payload.get('exp')
    iat_timestamp = payload.get('iat')
    
    if exp_timestamp:
        exp_time = datetime.fromtimestamp(exp_timestamp)
        current_time = datetime.now()
        
        print(f"\n[TIME] Time Information:")
        print(f"   Current Time: {current_time}")
        print(f"   Token Issued (iat): {datetime.fromtimestamp(iat_timestamp) if iat_timestamp else 'N/A'}")
        print(f"   Token Expires (exp): {exp_time}")
        
        if current_time > exp_time:
            time_expired = current_time - exp_time
            print(f"\n[FAIL] TOKEN EXPIRED!")
            print(f"   Expired: {time_expired} ago")
            return False, payload
        else:
            time_remaining = exp_time - current_time
            print(f"\n[PASS] TOKEN VALID!")
            print(f"   Time remaining: {time_remaining}")
            return True, payload
    else:
        print("[WARN] No expiry found in token")
        return None, payload


def test_upstox_api():
    """Test Upstox API with the current token."""
    print("\n" + "=" * 60)
    print("[TEST] TESTING UPSTOX API ENDPOINTS")
    print("=" * 60)
    
    token = os.getenv("UPSTOX_ACCESS_TOKEN", "")
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    tests = [
        {
            "name": "User Profile",
            "url": "https://api.upstox.com/v2/user/profile",
            "method": "GET"
        },
        {
            "name": "Market Quote (RELIANCE)",
            "url": "https://api.upstox.com/v2/market-quote/quotes?instrument_key=NSE_EQ%7CINE002A01018",
            "method": "GET"
        },
        {
            "name": "Historical Data (RELIANCE - 1 day)",
            "url": f"https://api.upstox.com/v2/historical-candle/NSE_EQ%7CINE002A01018/day/{datetime.now().strftime('%Y-%m-%d')}/{(datetime.now()).strftime('%Y-%m-%d')}",
            "method": "GET"
        }
    ]
    
    results = []
    
    for test in tests:
        print(f"\n[API] Testing: {test['name']}")
        print(f"   URL: {test['url'][:80]}...")
        
        try:
            response = requests.get(test['url'], headers=headers, timeout=10)
            status = response.status_code
            
            if status == 200:
                data = response.json()
                print(f"   [PASS] Status: {status} - SUCCESS")
                if data.get("status") == "success":
                    print(f"   [DATA] Response status: success")
                else:
                    print(f"   [DATA] Response: {json.dumps(data, indent=6)[:200]}...")
                results.append({"test": test['name'], "status": "PASS", "code": status})
            elif status == 401:
                print(f"   [FAIL] Status: {status} - UNAUTHORIZED (Token expired or invalid)")
                results.append({"test": test['name'], "status": "FAIL", "code": status, "reason": "Token expired/invalid"})
            else:
                print(f"   [WARN] Status: {status}")
                print(f"   Response: {response.text[:200]}...")
                results.append({"test": test['name'], "status": "WARN", "code": status})
        
        except requests.exceptions.Timeout:
            print(f"   [WARN] Request timed out")
            results.append({"test": test['name'], "status": "TIMEOUT"})
        except Exception as e:
            print(f"   [FAIL] Error: {e}")
            results.append({"test": test['name'], "status": "ERROR", "error": str(e)})
    
    return results


def test_backend_api():
    """Test our backend API endpoints."""
    print("\n" + "=" * 60)
    print("[TEST] TESTING BACKEND API ENDPOINTS")
    print("=" * 60)
    
    BASE_URL = "http://localhost:8000"
    
    # First, check if backend is running
    print("\n[API] Checking if backend is running...")
    try:
        health_response = requests.get(f"{BASE_URL}/health", timeout=5)
        if health_response.status_code == 200:
            print(f"   [PASS] Backend is running!")
        else:
            print(f"   [WARN] Backend returned status: {health_response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"   [FAIL] Backend is NOT running at {BASE_URL}")
        print("   Please start the backend with: python -m uvicorn main:app --reload")
        return []
    except Exception as e:
        print(f"   [FAIL] Error connecting to backend: {e}")
        return []
    
    # Login to get auth token
    print("\n[API] Logging in to get JWT token...")
    try:
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "demo@example.com", "password": "demo123"},
            timeout=10
        )
        
        if login_response.status_code != 200:
            print(f"   [FAIL] Login failed: {login_response.status_code}")
            print(f"   Response: {login_response.text}")
            return []
        
        jwt_token = login_response.json().get("access_token")
        print(f"   [PASS] Got JWT token: {jwt_token[:30]}...")
        
    except Exception as e:
        print(f"   [FAIL] Login error: {e}")
        return []
    
    headers = {"Authorization": f"Bearer {jwt_token}"}
    
    # Test backend endpoints
    tests = [
        {"name": "Dashboard Stats", "url": f"{BASE_URL}/api/trading/dashboard"},
        {"name": "Market Indices", "url": f"{BASE_URL}/api/trading/market-indices"},
        {"name": "Gainers/Losers", "url": f"{BASE_URL}/api/trading/gainers-losers"},
        {"name": "User Profile", "url": f"{BASE_URL}/api/auth/me"},
    ]
    
    results = []
    
    for test in tests:
        print(f"\n[API] Testing: {test['name']}")
        
        try:
            response = requests.get(test['url'], headers=headers, timeout=30)
            status = response.status_code
            
            if status == 200:
                data = response.json()
                print(f"   [PASS] Status: {status} - SUCCESS")
                # Pretty print a summary of the response
                if isinstance(data, dict):
                    keys = list(data.keys())[:5]
                    print(f"   [DATA] Response keys: {keys}")
                elif isinstance(data, list):
                    print(f"   [DATA] Response: List with {len(data)} items")
                results.append({"test": test['name'], "status": "PASS", "code": status})
            else:
                print(f"   [WARN] Status: {status}")
                print(f"   Response: {response.text[:200]}...")
                results.append({"test": test['name'], "status": "FAIL", "code": status})
        
        except requests.exceptions.Timeout:
            print(f"   [WARN] Request timed out (30s)")
            results.append({"test": test['name'], "status": "TIMEOUT"})
        except Exception as e:
            print(f"   [FAIL] Error: {e}")
            results.append({"test": test['name'], "status": "ERROR", "error": str(e)})
    
    return results


def print_summary(token_valid, upstox_results, backend_results):
    """Print a summary of all tests."""
    print("\n" + "=" * 60)
    print("[SUMMARY] TEST SUMMARY")
    print("=" * 60)
    
    # Token status
    if token_valid is True:
        print("\n[TOKEN] Upstox Token: VALID")
    elif token_valid is False:
        print("\n[TOKEN] Upstox Token: EXPIRED")
    else:
        print("\n[TOKEN] Upstox Token: UNKNOWN")
    
    # Upstox API results
    if upstox_results:
        print("\n[UPSTOX] Upstox API Tests:")
        for result in upstox_results:
            status_icon = "[PASS]" if result["status"] == "PASS" else "[FAIL]" if result["status"] == "FAIL" else "[WARN]"
            print(f"   {status_icon} {result['test']}: {result['status']}")
    
    # Backend API results
    if backend_results:
        print("\n[BACKEND] Backend API Tests:")
        for result in backend_results:
            status_icon = "[PASS]" if result["status"] == "PASS" else "[FAIL]" if result["status"] == "FAIL" else "[WARN]"
            print(f"   {status_icon} {result['test']}: {result['status']}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    # Check token expiry
    token_valid, payload = check_token_expiry()
    
    # Test Upstox API directly
    upstox_results = test_upstox_api()
    
    # Test backend API (if running)
    backend_results = test_backend_api()
    
    # Print summary
    print_summary(token_valid, upstox_results, backend_results)
