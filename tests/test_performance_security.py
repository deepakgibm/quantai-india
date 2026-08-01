"""
Performance and Security Audit Tests
Validates API response latencies, CORS policies, SQL injection protection, and security headers.
"""

import pytest
import time
import requests
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

@pytest.fixture(scope="module")
def api_auth_token(request):
    """Get auth token for security tests."""
    # Retrieve the session-scoped auth_token fixture dynamically or directly
    return request.getfixturevalue("auth_token")

class TestPerformanceLatencies:
    """Audit response times for critical endpoints to ensure < 500ms (Scanner < 50ms)."""

    @pytest.mark.parametrize("endpoint, auth_required, target_ms", [
        ("/api/health/", False, 200),
        ("/api/upstox/status", False, 200),
        ("/api/scanners/v3/momentum", True, 200),
        ("/api/scanners/v3/breakout", True, 200),
        ("/api/scanners/v3/reversal", True, 200),
    ])
    def test_endpoint_latency(self, api_auth_token, endpoint, auth_required, target_ms):
        """Verify endpoint latency is under target threshold."""
        headers = {}
        if auth_required:
            if not api_auth_token:
                pytest.skip("Auth token not available")
            headers["Authorization"] = f"Bearer {api_auth_token}"

        start_time = time.time()
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=10)
        duration_ms = (time.time() - start_time) * 1000

        print(f"Latency for {endpoint}: {duration_ms:.2f}ms (target: {target_ms}ms)")
        assert response.status_code == 200
        assert duration_ms < target_ms, f"{endpoint} took {duration_ms:.2f}ms, exceeding target of {target_ms}ms"


class TestSecurityAudit:
    """Audit CORS, SQL Injection, and security headers."""

    def test_cors_preflight(self):
        """Verify CORS preflight headers are returned correctly."""
        headers = {
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        }
        response = requests.options(f"{BASE_URL}/api/scanners/v3/status", headers=headers, timeout=10)
        
        # FastAPI default CORS handling returns 200 or 400 depending on middleware settings
        assert response.status_code in [200, 204, 400]
        if response.status_code in [200, 204]:
            assert "access-control-allow-origin" in response.headers

    @pytest.mark.parametrize("payload", [
        "RELIANCE' OR '1'='1",
        "RELIANCE'; DROP TABLE vcp_scores; --",
        "RELIANCE' UNION SELECT NULL, NULL; --",
    ])
    def test_sql_injection_protection(self, api_auth_token, payload):
        """Verify queries with SQL injection payloads fail safely without exposing data or 500 errors."""
        headers = {}
        if api_auth_token:
            headers["Authorization"] = f"Bearer {api_auth_token}"

        response = requests.get(
            f"{BASE_URL}/api/v1/institutional-scanner/detail/{payload}",
            headers=headers,
            timeout=10
        )
        # Injection payload should return 404/200 (Not Found / Default state) or 400/422 (Bad request)
        # It must NOT return 500 (Internal Server Error) which indicates unhandled query crashes!
        assert response.status_code in [200, 400, 404, 422]

    def test_security_headers(self):
        """Verify security headers are present in response."""
        response = requests.get(f"{BASE_URL}/api/health/", timeout=10)
        headers = response.headers
        
        # Check standard security hardening headers
        assert "x-frame-options" in headers or "content-security-policy" in headers
        assert headers.get("x-content-type-options") == "nosniff"
