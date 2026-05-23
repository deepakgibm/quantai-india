import pytest
import requests

BASE_URL = "http://localhost:8000"
TEST_EMAIL = "test_auth@quantai.com"
TEST_PASSWORD = "ValidPassword123!"

@pytest.fixture(scope="module")
def headers():
    """Login and get auth headers."""
    login_url = f"{BASE_URL}/api/auth/login"
    login_payload = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    r = requests.post(login_url, json=login_payload, timeout=10)
    assert r.status_code == 200, f"Login failed: {r.text}"
    token = r.json().get("access_token")
    assert token is not None
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

class TestDashboardFeatures:
    """Test dashboard features: Search, Volatility (with ATR), Option Flow, Heatmap."""

    def test_search_endpoint(self, headers):
        """Test the global search autocomplete endpoint."""
        url = f"{BASE_URL}/api/search/stocks?q=RELI"
        response = requests.get(url, headers=headers, timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "count" in data
        assert len(data["results"]) > 0
        
        # Verify first result fields
        first = data["results"][0]
        assert "symbol" in first
        assert "company_name" in first
        assert "instrument_key" in first

    def test_volatility_endpoint(self, headers):
        """Test the volatility dashboard calculation endpoint."""
        url = f"{BASE_URL}/api/volatility/RELIANCE?lookback_days=30"
        response = requests.get(url, headers=headers, timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "success"
        assert data.get("symbol") == "RELIANCE"
        assert "atr" in data
        assert "historical_volatility" in data
        assert "implied_volatility" in data
        assert "iv_rank" in data
        assert "iv_percentile" in data
        assert "regime" in data
        assert "mean_reversion_probability" in data
        assert "time_series" in data
        
        # Verify time series contains ATR
        time_series = data.get("time_series", [])
        assert len(time_series) > 0
        assert "date" in time_series[0]
        assert "price" in time_series[0]
        assert "volatility" in time_series[0]
        assert "atr" in time_series[0]

    def test_volatility_endpoint_invalid_lookback(self, headers):
        """Test lookback validation constraint on volatility endpoint (> 60 days)."""
        url = f"{BASE_URL}/api/volatility/RELIANCE?lookback_days=90"
        response = requests.get(url, headers=headers, timeout=10)
        assert response.status_code == 422  # Unprocessable Entity
        
        # Check details message
        data = response.json()
        assert not data.get("success")
        assert "error" in data or "detail" in data

    def test_option_flow_expiries_endpoint(self, headers):
        """Test option chain expiries endpoint."""
        url = f"{BASE_URL}/api/option-flow/RELIANCE/expiries"
        response = requests.get(url, headers=headers, timeout=10)
        assert response.status_code == 200
        envelope = response.json()
        assert envelope.get("success") is True
        data = envelope.get("data") or {}
        assert data.get("status") == "success"
        assert "expiries" in data
        assert isinstance(data["expiries"], list)
        assert len(data["expiries"]) > 0

    def test_option_flow_endpoint(self, headers):
        """Test option flow endpoint handles request cleanly and returns structured data or error."""
        url = f"{BASE_URL}/api/option-flow/RELIANCE"
        response = requests.get(url, headers=headers, timeout=10)
        assert response.status_code == 200
        envelope = response.json()
        assert "success" in envelope
        
        if envelope.get("success") is True:
            data = envelope.get("data") or {}
            assert "strikes" in data
            assert "block_deals" in data
            assert "sentiment" in data
            assert "pcr_oi" in data
        else:
            assert "error" in envelope
            assert envelope.get("data") is None

    def test_heatmap_endpoint(self, headers):
        """Test heatmap endpoint sector groupings and constituents."""
        url = f"{BASE_URL}/api/heatmap?mode=performance"
        response = requests.get(url, headers=headers, timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "success"
        assert "sectors" in data
        assert len(data["sectors"]) > 0
        
        # Verify sector schema
        first_sector = data["sectors"][0]
        assert "name" in first_sector
        assert "stocks" in first_sector
        assert len(first_sector["stocks"]) > 0
        
        # Verify stock schema
        first_stock = first_sector["stocks"][0]
        assert "symbol" in first_stock
        assert "name" in first_stock
        assert "price" in first_stock
        assert "change_pct" in first_stock
