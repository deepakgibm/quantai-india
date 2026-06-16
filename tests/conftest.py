"""
Pytest Configuration and Fixtures
Provides shared fixtures for API testing.
"""

import os
import sys
import pytest
import requests
from typing import Dict, Optional, Generator
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))

# Load environment variables
load_dotenv()
load_dotenv("config/.env")
load_dotenv("config/.env.test")

# =============================================================================
# Configuration
# =============================================================================

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
TEST_USERNAME = os.getenv("TEST_USERNAME", "dthat53@gmail.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "admin1243")

# =============================================================================
# Session-scoped fixtures
# =============================================================================

@pytest.fixture(scope="session")
def base_url() -> str:
    """Get base URL for API."""
    return BASE_URL


@pytest.fixture(scope="session")
def session() -> Generator[requests.Session, None, None]:
    """Create a requests session for all tests."""
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json"
    })
    yield s
    s.close()


@pytest.fixture(scope="session")
def auth_token(base_url: str, session: requests.Session) -> Optional[str]:
    """
    Get authentication token by logging in with test user.
    Creates user if doesn't exist.
    """
    # Try to login first
    login_data = {
        "email": TEST_USERNAME,
        "password": TEST_PASSWORD
    }
    
    try:
        response = session.post(
            f"{base_url}/api/auth/login",
            json=login_data,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        
        # If login fails (or validation error because user doesn't exist), try to create user
        if response.status_code in [401, 404, 422]:
            signup_data = {
                "email": TEST_USERNAME,
                "username": TEST_USERNAME.split("@")[0],
                "password": TEST_PASSWORD,
                "full_name": "Test User"
            }
            
            signup_response = session.post(
                f"{base_url}/api/auth/signup",
                json=signup_data,
                timeout=10
            )
            
            if signup_response.status_code in [200, 201]:
                # Now login
                login_response = session.post(
                    f"{base_url}/api/auth/login",
                    json=login_data,
                    timeout=10
                )
                if login_response.status_code == 200:
                    return login_response.json().get("access_token")
        
        print(f"Warning: Could not authenticate - {response.status_code}: {response.text}")
        return None
        
    except Exception as e:
        print(f"Warning: Authentication failed - {e}")
        return None


@pytest.fixture(scope="session")
def auth_headers(auth_token: Optional[str]) -> Dict[str, str]:
    """Get headers with authentication."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    return headers


@pytest.fixture(scope="session")
def api_client(base_url: str, session: requests.Session, auth_headers: Dict[str, str]):
    """
    API client for making requests.
    Returns a callable that handles both authenticated and public requests.
    """
    class APIClient:
        def __init__(self):
            self.base_url = base_url
            self.session = session
            self.auth_headers = auth_headers
            self.request_count = 0
            self.results = []
        
        def get(self, endpoint: str, auth: bool = True, **kwargs) -> requests.Response:
            url = f"{self.base_url}{endpoint}"
            headers = self.auth_headers.copy() if auth else {"Accept": "application/json"}
            if "headers" in kwargs:
                headers.update(kwargs.pop("headers"))
            self.request_count += 1
            return self.session.get(url, headers=headers, timeout=30, **kwargs)
        
        def post(self, endpoint: str, auth: bool = True, **kwargs) -> requests.Response:
            url = f"{self.base_url}{endpoint}"
            headers = self.auth_headers.copy() if auth else {"Accept": "application/json"}
            if "headers" in kwargs:
                headers.update(kwargs.pop("headers"))
            self.request_count += 1
            return self.session.post(url, headers=headers, timeout=30, **kwargs)
        
        def put(self, endpoint: str, auth: bool = True, **kwargs) -> requests.Response:
            url = f"{self.base_url}{endpoint}"
            headers = self.auth_headers.copy() if auth else {"Accept": "application/json"}
            if "headers" in kwargs:
                headers.update(kwargs.pop("headers"))
            self.request_count += 1
            return self.session.put(url, headers=headers, timeout=30, **kwargs)
        
        def delete(self, endpoint: str, auth: bool = True, **kwargs) -> requests.Response:
            url = f"{self.base_url}{endpoint}"
            headers = self.auth_headers.copy() if auth else {"Accept": "application/json"}
            if "headers" in kwargs:
                headers.update(kwargs.pop("headers"))
            self.request_count += 1
            return self.session.delete(url, headers=headers, timeout=30, **kwargs)
    
    return APIClient()


# =============================================================================
# Test data fixtures
# =============================================================================

@pytest.fixture(scope="session")
def test_symbols():
    """Get test symbols for price validation."""
    from tests.test_utils.test_data import TEST_SYMBOLS
    return TEST_SYMBOLS


@pytest.fixture(scope="session")
def quick_test_symbols():
    """Get quick test symbols (subset for fast tests)."""
    from tests.test_utils.test_data import QUICK_TEST_SYMBOLS
    return QUICK_TEST_SYMBOLS


@pytest.fixture(scope="session")
def symbol_to_instrument_key():
    """Get symbol to instrument key mapping."""
    from tests.test_utils.test_data import SYMBOL_TO_INSTRUMENT_KEY
    return SYMBOL_TO_INSTRUMENT_KEY


# =============================================================================
# Upstox reference fixtures
# =============================================================================

@pytest.fixture(scope="session")
def upstox_client():
    """Get Upstox reference client."""
    from tests.test_utils.upstox_reference import get_upstox_client
    return get_upstox_client()


# =============================================================================
# Reporting fixtures
# =============================================================================

@pytest.fixture(scope="session")
def test_report():
    """Create test report for aggregating results."""
    from tests.test_utils.validators import TestReport
    return TestReport()


# =============================================================================
# Pytest hooks
# =============================================================================

def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "price_validation: marks tests that validate price accuracy"
    )
    config.addinivalue_line(
        "markers", "api_health: marks tests that check API health"
    )


def pytest_sessionfinish(session, exitstatus):
    """Generate report after all tests complete."""
    # Report generation is handled in individual test modules
    pass


# =============================================================================
# Utility fixtures
# =============================================================================

@pytest.fixture
def market_is_open():
    """Check if market is currently open."""
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    weekday = now.weekday()
    
    # Market hours: Monday-Friday, 9:15 AM - 3:30 PM IST
    if weekday >= 5:  # Weekend
        return False
    
    if hour < 9 or hour > 15:
        return False
    
    if hour == 9 and minute < 15:
        return False
    
    if hour == 15 and minute > 30:
        return False
    
    return True
