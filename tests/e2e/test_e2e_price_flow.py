import pytest
import httpx
import json
import time
from unittest.mock import patch, MagicMock, AsyncMock
from main import app
from services.price_manager.price_cache import get_price_cache
from services.price_manager.models import PriceSource
from utils.auth import get_current_user

@pytest.fixture
def client():
    try:
        transport = httpx.ASGITransport(app=app)
        return httpx.AsyncClient(transport=transport, base_url="http://test")
    except (AttributeError, TypeError):
        return httpx.AsyncClient(app=app, base_url="http://test")

@pytest.mark.asyncio
async def test_e2e_price_retrieval_flow(client):
    # 1. Prepare cache and mocks
    cache = get_price_cache()
    cache.clear("RELIANCE")

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "test@quantai.com"
    mock_user.is_upstox_connected = True
    
    mock_quote = {
        "last_price": 2500.55,
        "volume": 1200000,
        "open": 2490.00,
        "high": 2520.00,
        "low": 2480.00,
        "close": 2500.55,
        "previous_close": 2485.20,
    }

    app.dependency_overrides[get_current_user] = lambda: mock_user

    # Patch the UpstoxClient dependency
    with patch('services.upstox_client.UpstoxClient.get_live_quote', new_callable=AsyncMock) as mock_get_quote:
        # Configure UpstoxClient to return our mock quote
        mock_get_quote.return_value = mock_quote
        
        async with client as ac:
            start_time = time.perf_counter()
            # First request: should trigger a cache miss and call UpstoxClient
            response_1 = await ac.get("/api/upstox/market-quote/RELIANCE")
            latency_1 = (time.perf_counter() - start_time) * 1000
            
            assert response_1.status_code == 200
            data_1 = response_1.json()
            assert data_1["status"] == "success"
            
            symbol_key = "NSE_EQ:RELIANCE"
            assert symbol_key in data_1["data"]
            assert data_1["data"][symbol_key]["last_price"] == 2500.55
            assert data_1["data"][symbol_key]["price_source"] == PriceSource.UPSTOX_REST.value
            
            # Verify UpstoxClient was called once
            assert mock_get_quote.call_count == 1
            
            # Second request: should hit cache and resolve immediately without calling UpstoxClient again
            start_time_2 = time.perf_counter()
            response_2 = await ac.get("/api/upstox/market-quote/RELIANCE")
            latency_2 = (time.perf_counter() - start_time_2) * 1000
            
            assert response_2.status_code == 200
            data_2 = response_2.json()
            assert data_2["status"] == "success"
            
            assert data_2["data"][symbol_key]["last_price"] == 2500.55
            assert data_2["data"][symbol_key]["price_source"] == PriceSource.UPSTOX_WS.value
            
            # Verify UpstoxClient was NOT called again
            assert mock_get_quote.call_count == 1
            
            print(f"\nE2E Latency - Miss: {latency_1:.2f}ms, Hit: {latency_2:.2f}ms")

    app.dependency_overrides.clear()
    cache.clear("RELIANCE")
