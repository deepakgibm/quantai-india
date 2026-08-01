import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from services.price_manager.price_service import PriceService, get_price_service
from services.price_manager.models import PriceSource

@pytest.fixture
def service():
    return PriceService()

@pytest.mark.asyncio
async def test_get_price_empty_symbol(service):
    res = await service.get_price("")
    assert res["symbol"] == "NONE"
    assert res["ltp"] == 0.0
    assert res["source"] == PriceSource.NONE.value

@pytest.mark.asyncio
async def test_get_price_request_deduplication(service):
    async def delayed_resolve(s):
        await asyncio.sleep(0.05)
        return {
            "ltp": 300.0,
            "prev_close": 295.0,
            "price_source": PriceSource.UPSTOX_REST.value
        }
    
    mock_resolve = AsyncMock(side_effect=delayed_resolve)
    
    with patch.object(service, '_resolve_price_dict', mock_resolve):
        # Fire concurrent requests for RELIANCE
        task1 = service.get_price("RELIANCE")
        task2 = service.get_price("RELIANCE")
        
        results = await asyncio.gather(task1, task2)
        
        # Verify both resolved to same value
        assert results[0]["ltp"] == 300.0
        assert results[1]["ltp"] == 300.0
        
        # Verify underlying resolve was called exactly ONCE due to request deduplication
        assert mock_resolve.call_count == 1

@pytest.mark.asyncio
async def test_get_price_resolution_exception(service):
    mock_resolve = AsyncMock(side_effect=ValueError("API connection failed"))
    with patch.object(service, '_resolve_price_dict', mock_resolve):
        res = await service.get_price("RELIANCE")
        # Verify graceful empty fallback when resolver throws exception
        assert res["symbol"] == "RELIANCE"
        assert res["ltp"] == 0.0
        assert res["source"] == PriceSource.NONE.value

@pytest.mark.asyncio
async def test_get_prices_bulk_empty_input(service):
    res = await service.get_prices_bulk([])
    assert res == {}
    
    res = await service.get_prices_bulk(["", "  "])
    assert res == {}

@pytest.mark.asyncio
async def test_get_prices_bulk_routing(service):
    # Mock repository methods
    # RELIANCE found in WS cache
    # TCS missed in WS cache, found in REST bulk
    # INFY missed in both (returns fallback default)
    
    mock_ws = AsyncMock(side_effect=lambda s: {
        "ltp": 2500.0,
        "prev_close": 2480.0,
        "price_source": PriceSource.UPSTOX_WS.value
    } if s == "RELIANCE" else None)
    
    mock_rest_bulk = AsyncMock(return_value={
        "TCS": {
            "ltp": 4000.0,
            "prev_close": 3950.0,
            "price_source": PriceSource.UPSTOX_REST.value
        }
    })
    
    with patch.object(service._repo, 'get_from_ws', mock_ws), \
         patch.object(service._repo, 'get_from_rest_bulk', mock_rest_bulk):
        
        symbols = ["RELIANCE", "TCS", "INFY"]
        results = await service.get_prices_bulk(symbols)
        
        # Verify RELIANCE (WS Cache hit)
        assert results["RELIANCE"]["ltp"] == 2500.0
        assert results["RELIANCE"]["source"] == PriceSource.UPSTOX_WS.value
        
        # Verify TCS (REST Bulk fallback hit)
        assert results["TCS"]["ltp"] == 4000.0
        assert results["TCS"]["source"] == PriceSource.UPSTOX_REST.value
        
        # Verify INFY (No source available, fallback empty DTO)
        assert results["INFY"]["ltp"] == 0.0
        assert results["INFY"]["source"] == PriceSource.NONE.value

@pytest.mark.asyncio
async def test_get_prices_bulk_rest_exception_handling(service):
    mock_ws = AsyncMock(return_value=None)
    mock_rest_bulk = AsyncMock(side_effect=Exception("REST network connection timeout"))
    
    with patch.object(service._repo, 'get_from_ws', mock_ws), \
         patch.object(service._repo, 'get_from_rest_bulk', mock_rest_bulk):
        
        results = await service.get_prices_bulk(["TCS"])
        # Should gracefully catch REST exception and return fallback default
        assert results["TCS"]["ltp"] == 0.0
        assert results["TCS"]["source"] == PriceSource.NONE.value

def test_build_dto_prev_close_reconstruction_failure(service):
    # Pass a dict where previous close is missing (or <= 0) and change_percent is not convertible to float
    data = {
        "ltp": 100.0,
        "prev_close": 0.0,
        "change_percent": "corrupt_value",
        "price_source": PriceSource.UPSTOX_REST.value
    }
    
    # Verify DTO builder handles parsing exception gracefully
    dto = service._build_dto("TCS", data)
    assert dto.previous_close == 0.0
    assert dto.change == 100.0  # since prev_close is 0

def test_get_price_service_singleton():
    s1 = get_price_service()
    s2 = get_price_service()
    assert s1 is s2
