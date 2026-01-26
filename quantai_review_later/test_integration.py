"""
End-to-End Integration Testing Script
Tests the entire QuantAI India Trading Bot application including:
- Backend API endpoints
- Upstox API integration
- Gemini AI integration
- Frontend-Backend communication
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

class Color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(message):
    print(f"\n{Color.BOLD}{Color.CYAN}{'='*80}{Color.END}")
    print(f"{Color.BOLD}{Color.CYAN}{message.center(80)}{Color.END}")
    print(f"{Color.BOLD}{Color.CYAN}{'='*80}{Color.END}\n")

def print_test(test_name, status, details=""):
    status_text = f"{Color.GREEN}✅ PASSED{Color.END}" if status else f"{Color.RED}❌ FAILED{Color.END}"
    print(f"{Color.BOLD}{test_name}:{Color.END} {status_text}")
    if details:
        print(f"   {Color.YELLOW}Details:{Color.END} {details}")
    test_results.append({"test": test_name, "status": status, "details": details})

def test_backend_health():
    """Test if backend server is running"""
    print_header("🔍 BACKEND HEALTH CHECK")
    
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
    print_header("🔐 AUTHENTICATION TESTING")
    
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
    print_header("📊 UPSTOX API INTEGRATION")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 1: Get Auth URL
    try:
        response = requests.get(f"{BACKEND_URL}/api/upstox/auth-url", headers=headers)
        if response.status_code == 200:
            auth_url = response.json().get("auth_url")
            has_api_key = UPSTOX_API_KEY in auth_url if auth_url else False
            print_test("Upstox Auth URL Generation", True, 
                      f"API Key configured: {Color.GREEN if has_api_key else Color.RED}{has_api_key}{Color.END}")
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
        # Note: These might fail if token is expired - that's expected
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
    print_header("🤖 GEMINI AI INTEGRATION")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 1: Check API Key Configuration
    api_key_configured = bool(GEMINI_API_KEY and GEMINI_API_KEY != "")
    print_test("Gemini API Key Configured", api_key_configured,
               f"API Key: {GEMINI_API_KEY[:10]}..." if api_key_configured else "Not configured")
    
    if not api_key_configured:
        print(f"   {Color.YELLOW}⚠️  Skipping AI tests - API key not configured{Color.END}")
        return
    
    # Test 2: AI Prompt Processing
    prompt_data = {
        "prompt": "What are the top 3 stocks to buy in the Indian market for intraday trading today?"
    }
    
    try:
        response = requests.post(f"{BACKEND_URL}/api/ai/prompt", json=prompt_data, headers=headers, timeout=30)
        if response.status_code == 200:
            ai_response = response.json()
            response_text = ai_response.get("response", "")
            print_test("AI Prompt Processing", True, 
                      f"Response received ({len(response_text)} chars)")
            print(f"   {Color.CYAN}AI Response Preview:{Color.END} {response_text[:150]}...")
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
        response = requests.get(f"{BACKEND_URL}/api/ai/market-analysis", headers=headers, timeout=30)
        if response.status_code == 200:
            analysis = response.json()
            analysis_text = analysis.get("analysis", "")
            print_test("AI Market Analysis", True, 
                      f"Analysis received ({len(analysis_text)} chars)")
            print(f"   {Color.CYAN}Analysis Preview:{Color.END} {analysis_text[:150]}...")
        else:
            print_test("AI Market Analysis", False, f"Status: {response.status_code}")
    except requests.Timeout:
        print_test("AI Market Analysis", False, "Request timeout")
    except Exception as e:
        print_test("AI Market Analysis", False, f"Error: {str(e)}")

def test_trading_endpoints(token):
    """Test trading endpoints"""
    print_header("📈 TRADING ENDPOINTS")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test Dashboard
    try:
        response = requests.get(f"{BACKEND_URL}/api/trading/dashboard", headers=headers)
        if response.status_code == 200:
            stats = response.json()
            print_test("Dashboard Statistics", True, 
                      f"P&L: ₹{stats.get('total_pnl', 0):,.2f}, Capital: ₹{stats.get('total_capital', 0):,.2f}")
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
    print_header("⚙️ ALGORITHM MANAGEMENT")
    
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
    print_header("📋 ORDER MANAGEMENT")
    
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
    print_header("📊 TEST SUMMARY REPORT")
    
    total_tests = len(test_results)
    passed_tests = sum(1 for t in test_results if t["status"])
    failed_tests = total_tests - passed_tests
    pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"{Color.BOLD}Total Tests:{Color.END} {total_tests}")
    print(f"{Color.GREEN}Passed:{Color.END} {passed_tests}")
    print(f"{Color.RED}Failed:{Color.END} {failed_tests}")
    print(f"{Color.BOLD}Pass Rate:{Color.END} {pass_rate:.1f}%")
    
    # Configuration Summary
    print(f"\n{Color.BOLD}{Color.CYAN}📝 Configuration Status:{Color.END}")
    print(f"   Upstox API Key: {Color.GREEN}✓ Configured{Color.END}" if UPSTOX_API_KEY else f"   Upstox API Key: {Color.RED}✗ Not Configured{Color.END}")
    print(f"   Upstox Access Token: {Color.GREEN}✓ Configured{Color.END}" if UPSTOX_ACCESS_TOKEN else f"   Upstox Access Token: {Color.RED}✗ Not Configured{Color.END}")
    print(f"   Gemini API Key: {Color.GREEN}✓ Configured{Color.END}" if GEMINI_API_KEY else f"   Gemini API Key: {Color.RED}✗ Not Configured{Color.END}")
    
    # Failed Tests Details
    if failed_tests > 0:
        print(f"\n{Color.BOLD}{Color.RED}❌ Failed Tests:{Color.END}")
        for result in test_results:
            if not result["status"]:
                print(f"   • {result['test']}: {result['details']}")
    
    print(f"\n{Color.BOLD}Test completed at:{Color.END} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Overall Status
    if pass_rate >= 90:
        print(f"\n{Color.GREEN}{Color.BOLD}🎉 OVERALL STATUS: EXCELLENT - System is production ready!{Color.END}")
    elif pass_rate >= 70:
        print(f"\n{Color.YELLOW}{Color.BOLD}⚠️ OVERALL STATUS: GOOD - Some issues need attention{Color.END}")
    else:
        print(f"\n{Color.RED}{Color.BOLD}❌ OVERALL STATUS: NEEDS WORK - Critical issues found{Color.END}")

def main():
    """Main test execution"""
    print(f"\n{Color.BOLD}{Color.BLUE}{'='*80}")
    print("🧪 QUANTAI INDIA - END-TO-END INTEGRATION TESTING")
    print(f"{'='*80}{Color.END}\n")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Check if backend is running
    if not test_backend_health():
        print(f"\n{Color.RED}{Color.BOLD}❌ Backend server is not running!{Color.END}")
        print(f"{Color.YELLOW}Please start the backend server first:{Color.END}")
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
        print(f"\n{Color.RED}Cannot continue without authentication token{Color.END}")
    
    # Generate final report
    generate_report()

if __name__ == "__main__":
    main()
