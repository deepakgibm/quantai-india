import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from services.price_manager.price_repository import PriceRepository
from services.price_manager.models import PriceSource

@pytest.fixture
def repo():
    with patch('services.price_manager.price_repository.get_price_cache') as mock_get_cache, \
         patch('services.price_manager.price_repository.get_price_validator') as mock_get_validator:
        mock_cache = MagicMock()
        mock_validator = MagicMock()
        mock_get_cache.return_value = mock_cache
        mock_get_validator.return_value = mock_validator
        
        pr = PriceRepository()
        pr._cache = mock_cache
        pr._validator = mock_validator
        yield pr

@pytest.mark.asyncio
async def test_get_from_ws_hit(repo):
    # Cache hit where validator approves
    mock_dict = {"ltp": 150.0}
    repo._cache.get.return_value = mock_dict
    repo._validator.validate_price_dict.return_value = True

    result = await repo.get_from_ws("RELIANCE")
    assert result is not None
    assert result["price_source"] == PriceSource.UPSTOX_WS.value
    assert result["ltp"] == 150.0
    repo._cache.get.assert_called_with("RELIANCE")
    repo._validator.validate_price_dict.assert_called_with("RELIANCE", mock_dict)

@pytest.mark.asyncio
async def test_get_from_ws_miss_or_invalid(repo):
    # Cache miss
    repo._cache.get.return_value = None
    assert await repo.get_from_ws("RELIANCE") is None

    # Cache hit but validator rejects
    repo._cache.get.return_value = {"ltp": -10.0}
    repo._validator.validate_price_dict.return_value = False
    assert await repo.get_from_ws("RELIANCE") is None

@pytest.mark.asyncio
async def test_get_from_rest_success(repo):
    # REST success flow
    repo._validator.validate_price_dict.return_value = True
    
    mock_info = MagicMock()
    mock_info.instrument_key = "NSE_EQ|INE002A01018"
    
    mock_client = MagicMock()
    mock_client.get_live_quote = AsyncMock(return_value={
        "last_price": 150.0,
        "previous_close": 148.0,
        "open": 149.0,
        "high": 151.0,
        "low": 148.0,
        "close": 150.0,
        "volume": 5000
    })

    with patch('services.instrument_resolver.resolve_instrument_info', return_value=mock_info), \
         patch('services.upstox_client.get_upstox_client', return_value=mock_client):
        
        result = await repo.get_from_rest("RELIANCE")
        
        assert result is not None
        assert result["ltp"] == 150.0
        assert result["price_source"] == PriceSource.UPSTOX_REST.value
        repo._cache.set.assert_called()

@pytest.mark.asyncio
async def test_get_from_rest_failure(repo):
    # Resolution info fails or returns None
    with patch('services.instrument_resolver.resolve_instrument_info', return_value=None):
        assert await repo.get_from_rest("RELIANCE") is None

    # Client quote fails (exception raised)
    mock_info = MagicMock()
    mock_info.instrument_key = "NSE_EQ|INE002A01018"
    mock_client = MagicMock()
    mock_client.get_live_quote = AsyncMock(side_effect=Exception("Timeout"))

    with patch('services.instrument_resolver.resolve_instrument_info', return_value=mock_info), \
         patch('services.upstox_client.get_upstox_client', return_value=mock_client):
        assert await repo.get_from_rest("RELIANCE") is None

@pytest.mark.asyncio
async def test_get_from_rest_bulk(repo):
    repo._validator.validate_price_dict.return_value = True

    mock_info1 = MagicMock()
    mock_info1.instrument_key = "NSE_EQ|INE002A01018"
    mock_info1.exchange = "NSE"
    mock_info1.series = "EQ"
    mock_info1.symbol = "RELIANCE"

    mock_info2 = MagicMock()
    mock_info2.instrument_key = "NSE_EQ|INE467B01029"
    mock_info2.exchange = "NSE"
    mock_info2.series = "EQ"
    mock_info2.symbol = "TCS"

    mock_client = MagicMock()
    mock_client.get_live_quotes = AsyncMock(return_value={
        "NSE_EQ|INE002A01018": {"last_price": 150.0, "previous_close": 148.0},
        "NSE_EQ|INE467B01029": {"last_price": 3000.0, "previous_close": 2980.0}
    })

    def mock_resolver(sym):
        if sym.upper() == "RELIANCE":
            return mock_info1
        if sym.upper() == "TCS":
            return mock_info2
        return None

    with patch('services.instrument_resolver.resolve_instrument_info', side_effect=mock_resolver), \
         patch('services.upstox_client.get_upstox_client', return_value=mock_client):
        
        result = await repo.get_from_rest_bulk(["RELIANCE", "TCS"])
        
        assert "RELIANCE" in result
        assert "TCS" in result
        assert result["RELIANCE"]["ltp"] == 150.0
        assert result["TCS"]["ltp"] == 3000.0
        assert repo._cache.set.call_count == 2

@pytest.mark.asyncio
async def test_database_fallback_is_disabled(repo):
    # Phase 7 spec: Database fallback is disabled for live prices
    assert await repo.get_from_db("RELIANCE") is None
    assert await repo.get_from_db_bulk(["RELIANCE", "TCS"]) == {}

@pytest.mark.asyncio
async def test_get_from_rest_bulk_empty(repo):
    assert await repo.get_from_rest_bulk([]) == {}

@pytest.mark.asyncio
async def test_get_from_rest_bulk_exception(repo):
    mock_client = MagicMock()
    mock_client.get_live_quotes = AsyncMock(side_effect=Exception("Bulk API failed"))
    
    mock_info = MagicMock()
    mock_info.instrument_key = "NSE_EQ|INE002A01018"
    
    with patch('services.instrument_resolver.resolve_instrument_info', return_value=mock_info), \
         patch('services.upstox_client.get_upstox_client', return_value=mock_client):
        result = await repo.get_from_rest_bulk(["RELIANCE"])
        assert result == {}

