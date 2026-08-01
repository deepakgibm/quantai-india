import pytest
import httpx
from main import app
from unittest.mock import patch, MagicMock
from utils.auth import get_current_user

@pytest.fixture
def client():
    try:
        transport = httpx.ASGITransport(app=app)
        return httpx.AsyncClient(transport=transport, base_url="http://test")
    except (AttributeError, TypeError):
        return httpx.AsyncClient(app=app, base_url="http://test")

@pytest.mark.asyncio
async def test_market_quote_contract_success(client):
    # Mock price service return value
    mock_price_data = {
        "symbol": "RELIANCE",
        "instrument_key": "NSE_EQ|INE002A01018",
        "ltp": 2500.55,
        "open": 2490.0,
        "high": 2520.0,
        "low": 2480.0,
        "close": 2500.55,
        "previous_close": 2485.20,
        "change": 15.35,
        "change_percent": 0.62,
        "volume": 1200000,
        "timestamp": "2026-07-24T15:30:00+05:30",
        "market_status": "CLOSED",
        "source": "UPSTOX_WS",
        "last_updated": "2026-07-24T15:35:00+05:30"
    }

    # Mock user
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "test@quantai.com"
    mock_user.is_upstox_connected = True

    # Use FastAPI dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with patch('services.price_manager.price_service.PriceService.get_price', return_value=mock_price_data):
        async with client as ac:
            response = await ac.get("/api/upstox/market-quote/RELIANCE")
            
            assert response.status_code == 200
            resp_data = response.json()
            
            assert resp_data["status"] == "success"
            symbol_key = "NSE_EQ:RELIANCE"
            assert symbol_key in resp_data["data"]
            
            quote = resp_data["data"][symbol_key]
            assert quote["last_price"] == 2500.55
            assert quote["previous_close"] == 2485.20
            assert quote["volume"] == 1200000

    # Clean up overrides
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_market_quote_contract_error(client):
    mock_user = MagicMock()
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with patch('services.price_manager.price_service.PriceService.get_price', side_effect=Exception("API Connection Denied")):
        async with client as ac:
            response = await ac.get("/api/upstox/market-quote/RELIANCE")
            
            assert response.status_code == 200
            resp_data = response.json()
            
            assert resp_data["status"] == "error"
            assert "API Connection Denied" in resp_data["message"]
            assert resp_data["data"] is None

    app.dependency_overrides.clear()
