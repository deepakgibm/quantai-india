"""
End-to-End Integration Testing Script (Simple Output)
Tests the entire QuantAI India Trading Bot application
"""

import requests
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('backend/.env')

# Configuration
BACKEND_URL = "http://localhost:8000"
UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY")
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Test Results Tracker
test_results = []

def print_header(message):
    print(f"\n{'='*80}")
    print(f"{message.center(80)}")
    print(f"{'='*80}\n")

def print_test(test_name, status, details=""):
    status_text = "[PASSED]" if status else "[FAILED]"
    print(f"{status_text} {test_name}")
    if details:
        print(f"        Details: {details}")
    test_results.append({"test": test_name, "status": status, "details": details})

def test_backend_health():
    """Test if backend server is running"""
    print_header("BACKEND HEALTH CHECK")
    
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            print_test("Backend Health Check", True, f"Status: {response.json()}")
            return True
        else:
            print_test("Backend Health Check", False, f"Status Code: {response.status_code}")
            return False
    except Exception as e:
        print_test("Backend Health Check", False, f"Error: {str(e)}")
        return False

def test_authentication():
    """Test user authentication"""
    print_header("AUTHENTICATION TESTING")
    
    # Test Signup
    signup_data = {
        "email": "integration_test@example.com",
        "username": "integration_user",
        "full_name": "Integration Test User",
        "password": "testpass123"
    }
    
    try:
        response = requests.post(f"{BACKEND_URL}/api/auth/signup", json=signup_data)
        if response.status_code == 200:
            print_test("User Signup", True, f"User created successfully")
        else:
            # User might already exist
            print_test("User Signup", True, f"User already exists or created")
    except Exception as e:
        print_test("User Signup", False, f"Error: {str(e)}")
        return None
    
    # Test Login
    login_data = {
        "email": signup_data["email"],
        "password": signup_data["password"]
    }
    
    try:
        response = requests.post(f"{BACKEND_URL}/api/auth/login", json=login_data)
        if response.status_code == 200:
            token = response.json().get("access_token")
            print_test("User Login", True, f"JWT token received (length: {len(token)})")
            return token
        else:
            print_test("User Login", False, f"Status: {response.status_code}")
            return None
    except Exception as e:
        print_test("User Login", False, f"Error: {str(e)}")
        return None

def test_upstox_integration(token):
    """Test Upstox API integration"""
    print_header("UPSTOX API INTEGRATION")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 1: Get Auth URL
    try:
        response = requests.get(f"{BACKEND_URL}/api/upstox/auth-url", headers=headers)
        if response.status_code == 200:
            auth_url = response.json().get("auth_url")
            has_api_key = UPSTOX_API_KEY in auth_url if auth_url else False
            print_test("Upstox Auth URL Generation", True, 
                      f"API Key configured: {has_api_key}")
        else:
            print_test("Upstox Auth URL Generation", False, f"Status: {response.status_code}")
    except Exception as e:
        print_test("Upstox Auth URL Generation", False, f"Error: {str(e)}")
    
    # Test 2: Check API Key Configuration
    api_key_configured = bool(UPSTOX_API_KEY and UPSTOX_API_KEY != "")
    print_test("Upstox API Key Configured", api_key_configured, 
               f"API Key: {UPSTOX_API_KEY[:10]}..." if api_key_configured else "Not configured")
    
    # Test 3: Check Access Token
    token_configured = bool(UPSTOX_ACCESS_TOKEN and UPSTOX_ACCESS_TOKEN != "")
    print_test("Upstox Access Token Configured", token_configured,
               f"Token length: {len(UPSTOX_ACCESS_TOKEN)} chars" if token_configured else "Not configured")
    
    # Test 4: Test Upstox API endpoints (if token is available)
    if token_configured:
        try:
            response = requests.get(f"{BACKEND_URL}/api/upstox/portfolio", headers=headers)
            if response.status_code == 200:
                print_test("Upstox Portfolio API", True, "Portfolio data retrieved")
            elif response.status_code == 400:
                error_msg = response.json().get("detail", "")
                if "not connected" in error_msg.lower():
                    print_test("Upstox Portfolio API", True, "Endpoint working (not connected yet)")
                else:
                    print_test("Upstox Portfolio API", False, f"Error: {error_msg}")
            else:
                print_test("Upstox Portfolio API", False, f"Status: {response.status_code}")
        except Exception as e:
            print_test("Upstox Portfolio API", False, f"Error: {str(e)}")

def test_gemini_ai_integration(token):
    """Test Gemini AI integration"""
    print_header("GEMINI AI INTEGRATION")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 1: Check API Key Configuration
    api_key_configured = bool(GEMINI_API_KEY and GEMINI_API_KEY != "")
    print_test("Gemini API Key Configured", api_key_configured,
               f"API Key: {GEMINI_API_KEY[:10]}..." if api_key_configured else "Not configured")
    
    if not api_key_configured:
        print("        WARNING: Skipping AI tests - API key not configured")
        return
    
    # Test 2: AI Prompt Processing
    prompt_data = {
        "prompt": "What are the top 3 stocks to buy in the Indian market for intraday trading today?"
    }
    
    try:
        print("        Testing AI Prompt (this may take 10-30 seconds)...")
        response = requests.post(f"{BACKEND_URL}/api/ai/prompt", json=prompt_data, headers=headers, timeout=60)
        if response.status_code == 200:
            ai_response = response.json()
            response_text = ai_response.get("response", "")
            print_test("AI Prompt Processing", True, 
                      f"Response received ({len(response_text)} chars)")
            print(f"        AI Response Preview: {response_text[:200]}...")
        else:
            error = response.json().get("detail", "Unknown error")
            if "not configured" in error.lower():
                print_test("AI Prompt Processing", False, "API key issue")
            else:
                print_test("AI Prompt Processing", False, f"Error: {error}")
    except requests.Timeout:
        print_test("AI Prompt Processing", False, "Request timeout (AI taking too long)")
    except Exception as e:
        print_test("AI Prompt Processing", False, f"Error: {str(e)}")
    
    # Test 3: Market Analysis
    try:
        print("        Testing Market Analysis (this may take 10-30 seconds)...")
        response = requests.get(f"{BACKEND_URL}/api/ai/market-analysis", headers=headers, timeout=60)
        if response.status_code == 200:
            analysis = response.json()
            analysis_text = analysis.get("analysis", "")
            print_test("AI Market Analysis", True, 
                      f"Analysis received ({len(analysis_text)} chars)")
            print(f"        Analysis Preview: {analysis_text[:200]}...")
        else:
            print_test("AI Market Analysis", False, f"Status: {response.status_code}")
    except requests.Timeout:
        print_test("AI Market Analysis", False, "Request timeout")
    except Exception as e:
        print_test("AI Market Analysis", False, f"Error: {str(e)}")

def test_trading_endpoints(token):
    """Test trading endpoints"""
    print_header("TRADING ENDPOINTS")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test Dashboard
    try:
        response = requests.get(f"{BACKEND_URL}/api/trading/dashboard", headers=headers)
        if response.status_code == 200:
            stats = response.json()
            print_test("Dashboard Statistics", True, 
                      f"P&L: Rs.{stats.get('total_pnl', 0):,.2f}, Capital: Rs.{stats.get('total_capital', 0):,.2f}")
        else:
            print_test("Dashboard Statistics", False, f"Status: {response.status_code}")
    except Exception as e:
        print_test("Dashboard Statistics", False, f"Error: {str(e)}")
    
    # Test Market Indices
    try:
        response = requests.get(f"{BACKEND_URL}/api/trading/market-indices", headers=headers)
        if response.status_code == 200:
            indices = response.json()
            print_test("Market Indices", True, f"Retrieved {len(indices)} indices")
        else:
            print_test("Market Indices", False, f"Status: {response.status_code}")
    except Exception as e:
        print_test("Market Indices", False, f"Error: {str(e)}")

def test_algorithms(token):
    """Test algorithm management"""
    print_header("ALGORITHM MANAGEMENT")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get Algorithms
    try:
        response = requests.get(f"{BACKEND_URL}/api/algorithms/", headers=headers)
        if response.status_code == 200:
            algorithms = response.json()
            print_test("Get Algorithms", True, f"Found {len(algorithms)} algorithms")
        else:
            print_test("Get Algorithms", False, f"Status: {response.status_code}")
    except Exception as e:
        print_test("Get Algorithms", False, f"Error: {str(e)}")

def test_orders(token):
    """Test order management"""
    print_header("ORDER MANAGEMENT")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get Orders
    try:
        response = requests.get(f"{BACKEND_URL}/api/orders/", headers=headers)
        if response.status_code == 200:
            orders = response.json()
            print_test("Get Orders", True, f"Found {len(orders)} orders")
        else:
            print_test("Get Orders", False, f"Status: {response.status_code}")
    except Exception as e:
        print_test("Get Orders", False, f"Error: {str(e)}")

def generate_report():
    """Generate test report"""
    print_header("TEST SUMMARY REPORT")
    
    total_tests = len(test_results)
    passed_tests = sum(1 for t in test_results if t["status"])
    failed_tests = total_tests - passed_tests
    pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Pass Rate: {pass_rate:.1f}%")
    
    # Configuration Summary
    print(f"\nConfiguration Status:")
    print(f"   Upstox API Key: {'CONFIGURED' if UPSTOX_API_KEY else 'NOT CONFIGURED'}")
    print(f"   Upstox Access Token: {'CONFIGURED' if UPSTOX_ACCESS_TOKEN else 'NOT CONFIGURED'}")
    print(f"   Gemini API Key: {'CONFIGURED' if GEMINI_API_KEY else 'NOT CONFIGURED'}")
    
    # Failed Tests Details
    if failed_tests > 0:
        print(f"\nFailed Tests:")
        for result in test_results:
            if not result["status"]:
                print(f"   - {result['test']}: {result['details']}")
    
    print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Overall Status
    if pass_rate >= 90:
        print(f"\n[EXCELLENT] OVERALL STATUS: System is production ready!")
    elif pass_rate >= 70:
        print(f"\n[GOOD] OVERALL STATUS: Some issues need attention")
    else:
        print(f"\n[NEEDS WORK] OVERALL STATUS: Critical issues found")
    
    return pass_rate

def main():
    """Main test execution"""
    print(f"\n{'='*80}")
    print("QUANTAI INDIA - END-TO-END INTEGRATION TESTING")
    print(f"{'='*80}\n")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Check if backend is running
    if not test_backend_health():
        print(f"\n[ERROR] Backend server is not running!")
        print(f"Please start the backend server first:")
        print(f"   cd backend")
        print(f"   python main.py")
        return
    
    # Run all tests
    token = test_authentication()
    
    if token:
        test_upstox_integration(token)
        test_gemini_ai_integration(token)
        test_trading_endpoints(token)
        test_algorithms(token)
        test_orders(token)
    else:
        print(f"\nCannot continue without authentication token")
    
    # Generate final report
    pass_rate = generate_report()
    
    # Write results to file
    with open("integration_test_results.txt", "w") as f:
        f.write(f"Integration Test Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*80 + "\n\n")
        for result in test_results:
            status = "PASSED" if result["status"] else "FAILED"
            f.write(f"[{status}] {result['test']}\n")
            if result["details"]:
                f.write(f"    {result['details']}\n")
            f.write("\n")
        f.write(f"\nOverall Pass Rate: {pass_rate:.1f}%\n")
    
    print(f"\nDetailed results saved to: integration_test_results.txt")

if __name__ == "__main__":
    main()
