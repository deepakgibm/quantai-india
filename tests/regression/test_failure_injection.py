import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from services.price_manager.price_service import PriceService
from services.price_manager.price_cache import PriceCache
from services.price_manager.price_validator import PriceValidator
from services.price_manager.models import PriceSource

@pytest.fixture
def service():
    return PriceService()

@pytest.mark.asyncio
async def test_failure_upstox_unavailable(service):
    # Simulate Upstox REST API completely unavailable (raises Exception)
    with patch('services.price_manager.price_cache.PriceCache.get', return_value=None), \
         patch('services.upstox_client.UpstoxClient.get_live_quote', side_effect=Exception("Upstox connection refused")):
        
        result = await service.get_price("RELIANCE")
        
        # Verify fallback response
        assert result is not None
        assert result["symbol"] == "RELIANCE"
        assert result["ltp"] == 0.0
        assert result["source"] == PriceSource.NONE.value

@pytest.mark.asyncio
async def test_failure_upstox_timeout(service):
    # Simulate Upstox timeout (timeout exception)
    import httpx
    timeout_err = httpx.ReadTimeout("Request timed out")
    with patch('services.price_manager.price_cache.PriceCache.get', return_value=None), \
         patch('services.upstox_client.UpstoxClient.get_live_quote', side_effect=timeout_err):
        
        result = await service.get_price("RELIANCE")
        assert result["ltp"] == 0.0
        assert result["source"] == PriceSource.NONE.value

@pytest.mark.asyncio
async def test_failure_upstox_rate_limited(service):
    # Simulate Upstox HTTP 429 Rate Limiting
    import httpx
    request = httpx.Request("GET", "https://api.upstox.com/v2")
    response = httpx.Response(429, request=request)
    http_err = httpx.HTTPStatusError("Rate Limit Exceeded", request=request, response=response)
    
    with patch('services.price_manager.price_cache.PriceCache.get', return_value=None), \
         patch('services.upstox_client.UpstoxClient.get_live_quote', side_effect=http_err):
        
        result = await service.get_price("RELIANCE")
        assert result["ltp"] == 0.0
        assert result["source"] == PriceSource.NONE.value

@pytest.mark.asyncio
async def test_failure_redis_down(service):
    # Simulate Redis/Dragonfly down (is_available returns False or calls throw connection error)
    cache = service._repo._cache
    
    with patch.object(cache._cache, 'is_available', return_value=False), \
         patch('services.upstox_client.UpstoxClient.get_live_quote', return_value={"last_price": 100.0, "previous_close": 98.0}):
        
        # Clear local cache first
        cache._local_cache.clear()
        
        # First lookup: miss in local cache, fallback to REST
        result1 = await service.get_price("RELIANCE")
        assert result1["ltp"] == 100.0
        assert result1["source"] == PriceSource.UPSTOX_REST.value
        
        # Second lookup: should hit the local in-memory cache directly
        result2 = await service.get_price("RELIANCE")
        assert result2["ltp"] == 100.0
        assert result2["source"] == PriceSource.UPSTOX_WS.value  # local cache hit retrieves it

@pytest.mark.asyncio
async def test_failure_cache_corruption(service):
    # Simulate corrupt JSON inside cache (raises ValueError/json.JSONDecodeError)
    cache = service._repo._cache
    cache._local_cache.clear()
    
    with patch.object(cache._cache, 'is_available', return_value=True), \
         patch.object(cache._cache, 'get', return_value="invalid{corrupt_json]"), \
         patch('services.upstox_client.UpstoxClient.get_live_quote', return_value={"last_price": 120.0, "previous_close": 118.0}):
        
        # Cache retrieve fails due to corrupt json string -> acts as a miss and fetches from REST
        result = await service.get_price("RELIANCE")
        assert result["ltp"] == 120.0
        assert result["source"] == PriceSource.UPSTOX_REST.value
