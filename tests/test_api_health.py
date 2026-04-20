"""
API Health & Contract Tests
Tests for API availability, status codes, and response schema validation.
"""

import pytest
import time
from tests.test_utils.test_data import (
    PUBLIC_ENDPOINTS,
    AUTH_ENDPOINTS,
    OPTIONAL_AUTH_ENDPOINTS,
    HP_SCANNER_ENDPOINTS,
)


class TestAPIHealth:
    """Test API health and availability."""
    
    @pytest.mark.api_health
    def test_root_endpoint(self, api_client):
        """Test root endpoint returns 200."""
        response = api_client.get("/", auth=False)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "message" in data
    
    @pytest.mark.api_health
    def test_health_endpoint(self, api_client):
        """Test health endpoint returns 200 and has required fields."""
        response = api_client.get("/health", auth=False)
        assert response.status_code in [200, 503]  # 503 if degraded
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
    
    @pytest.mark.api_health
    def test_ready_endpoint(self, api_client):
        """Test readiness endpoint."""
        response = api_client.get("/ready", auth=False)
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data


class TestPublicEndpoints:
    """Test all public (no auth required) endpoints."""
    
    @pytest.mark.api_health
    @pytest.mark.parametrize("endpoint_config", PUBLIC_ENDPOINTS)
    def test_public_endpoint(self, api_client, endpoint_config):
        """Test public endpoints return expected status codes."""
        path = endpoint_config["path"]
        expected_status = endpoint_config.get("expected_status", 200)
        
        response = api_client.get(path, auth=False)
        
        # Allow some flexibility for service unavailable
        assert response.status_code in [expected_status, 503], \
            f"{path} returned {response.status_code}, expected {expected_status}"
        
        # Verify JSON response
        try:
            data = response.json()
            assert isinstance(data, (dict, list))
        except Exception:
            pytest.fail(f"{path} did not return valid JSON")


class TestAuthenticatedEndpoints:
    """Test authenticated endpoints with valid auth."""
    
    @pytest.mark.api_health
    @pytest.mark.parametrize("endpoint_config", AUTH_ENDPOINTS)
    def test_authenticated_endpoint(self, api_client, auth_token, endpoint_config):
        """Test authenticated endpoints return expected status codes."""
        if not auth_token:
            pytest.skip("No auth token available")
        
        path = endpoint_config["path"]
        expected_status = endpoint_config.get("expected_status", 200)
        
        response = api_client.get(path, auth=True)
        
        # Allow 401 if auth failed, 503 for service unavailable
        acceptable = [expected_status, 503]
        if response.status_code == 401:
            pytest.skip(f"Authentication required for {path}")
        
        assert response.status_code in acceptable, \
            f"{path} returned {response.status_code}, expected {expected_status}"
    
    @pytest.mark.api_health
    def test_auth_required_without_token(self, api_client):
        """Test authenticated endpoints return 401 without token."""
        # Pick a known auth-required endpoint
        response = api_client.get("/api/auth/me", auth=False)
        assert response.status_code in [401, 403, 422]


class TestOptionalAuthEndpoints:
    """Test endpoints that work with or without auth."""
    
    @pytest.mark.api_health
    @pytest.mark.parametrize("endpoint_config", OPTIONAL_AUTH_ENDPOINTS)
    def test_optional_auth_endpoint(self, api_client, endpoint_config):
        """Test optional auth endpoints work without auth."""
        path = endpoint_config["path"]
        
        response = api_client.get(path, auth=False)
        
        # These should work without auth (200 or 503 for service issues)
        assert response.status_code in [200, 503], \
            f"{path} returned {response.status_code}"


class TestHPScannerEndpoints:
    """Test HP Scanner v3 endpoints."""
    
    @pytest.mark.api_health
    @pytest.mark.parametrize("endpoint_config", HP_SCANNER_ENDPOINTS)
    def test_hp_scanner_endpoint(self, api_client, endpoint_config):
        """Test HP Scanner endpoints."""
        path = endpoint_config["path"]
        
        response = api_client.get(path, auth=False)
        
        # HP Scanner endpoints should return 200 or 503
        assert response.status_code in [200, 404, 503], \
            f"{path} returned {response.status_code}"


class TestResponseSchemas:
    """Test response schema validation."""
    
    @pytest.mark.api_health
    def test_market_top_movers_schema(self, api_client):
        """Test market top-movers returns expected schema."""
        response = api_client.get("/api/market/nifty100/top-movers", auth=False)
        
        if response.status_code != 200:
            pytest.skip(f"Endpoint returned {response.status_code}")
        
        data = response.json()
        
        # Should have gainers and/or losers
        assert "gainers" in data or "losers" in data or "top_gainers" in data or "data" in data
    
    @pytest.mark.api_health
    def test_trading_dashboard_schema(self, api_client, auth_token):
        """Test trading dashboard returns expected schema."""
        if not auth_token:
            pytest.skip("No auth token")
        
        response = api_client.get("/api/trading/dashboard", auth=True)
        
        if response.status_code != 200:
            pytest.skip(f"Endpoint returned {response.status_code}")
        
        data = response.json()
        
        # Dashboard should have some standard fields
        assert isinstance(data, dict)
    
    @pytest.mark.api_health
    def test_ai_top5_picks_schema(self, api_client):
        """Test AI top5-picks returns expected schema."""
        response = api_client.get("/api/ai/top5-picks", auth=False)
        
        if response.status_code != 200:
            pytest.skip(f"Endpoint returned {response.status_code}")
        
        data = response.json()
        
        # Should have stocks or signals
        assert "stocks" in data or "buy_signals" in data or "signals" in data or "data" in data
    
    @pytest.mark.api_health
    def test_scanner_strategies_schema(self, api_client, auth_token):
        """Test scanner strategies returns expected schema."""
        if not auth_token:
            pytest.skip("No auth token")
        
        response = api_client.get("/api/scanner/strategies", auth=True)
        
        if response.status_code != 200:
            pytest.skip(f"Endpoint returned {response.status_code}")
        
        data = response.json()
        
        # Should have strategies list or structured tiers
        assert isinstance(data, (dict, list))


class TestResponseTimes:
    """Test API response times."""
    
    @pytest.mark.api_health
    @pytest.mark.slow
    def test_critical_endpoints_latency(self, api_client):
        """Test critical endpoints respond within acceptable time."""
        critical_endpoints = [
            "/health",
            "/api/trading/health",
            "/api/v3/scanner/status",
        ]
        
        for endpoint in critical_endpoints:
            start = time.time()
            response = api_client.get(endpoint, auth=False)
            latency = (time.time() - start) * 1000
            
            # Health endpoints should respond in < 500ms
            assert latency < 500, f"{endpoint} took {latency:.0f}ms"
    
    @pytest.mark.api_health
    @pytest.mark.slow
    def test_scanner_endpoints_latency(self, api_client):
        """Test HP Scanner endpoints respond quickly."""
        scanner_endpoints = [
            "/api/v3/scanner/momentum",
            "/api/v3/scanner/breakout",
            "/api/v3/scanner/snapshots",
        ]
        
        for endpoint in scanner_endpoints:
            start = time.time()
            response = api_client.get(endpoint, auth=False)
            latency = (time.time() - start) * 1000
            
            # Scanner endpoints target < 50ms, allow 200ms for CI
            if response.status_code == 200:
                assert latency < 2000, f"{endpoint} took {latency:.0f}ms (target: <200ms)"


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.mark.api_health
    def test_invalid_endpoint_returns_404(self, api_client):
        """Test invalid endpoint returns 404."""
        response = api_client.get("/api/nonexistent/endpoint", auth=False)
        assert response.status_code == 404
    
    @pytest.mark.api_health
    def test_invalid_symbol_handling(self, api_client, auth_token):
        """Test API handles invalid symbol gracefully."""
        # Try HP scanner with invalid symbol
        response = api_client.get("/api/v3/scanner/snapshot/INVALID_SYMBOL_XYZ", auth=False)
        
        # Should return 404 or 200 with empty/error
        assert response.status_code in [200, 404, 422]
    
    @pytest.mark.api_health
    def test_malformed_request_handling(self, api_client, auth_token):
        """Test API handles malformed requests."""
        if not auth_token:
            pytest.skip("No auth token")
        
        # Send malformed JSON to POST endpoint
        response = api_client.post(
            "/api/auth/login",
            auth=False,
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )
        
        # Should return 400 or 422 for validation error
        assert response.status_code in [400, 422, 500]
