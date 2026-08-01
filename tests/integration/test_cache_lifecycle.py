import pytest
import json
from unittest.mock import patch, MagicMock
from services.price_manager.price_cache import PriceCache
from services.price_manager.models import MarketStatus

@pytest.fixture
def cache():
    with patch('services.price_manager.price_cache.get_cache_manager') as mock_get_mgr, \
         patch('services.price_manager.price_cache.get_market_status_service') as mock_get_status_svc:
        mock_mgr = MagicMock()
        mock_status_svc = MagicMock()
        mock_get_mgr.return_value = mock_mgr
        mock_get_status_svc.return_value = mock_status_svc
        
        pc = PriceCache()
        pc._cache = mock_mgr
        pc._status_service = mock_status_svc
        yield pc

def test_cache_get_hit_redis(cache):
    # Redis is available and has the key
    cache._cache.is_available.return_value = True
    cache._cache.get.side_effect = lambda k: json.dumps({"ltp": 150.0}) if "price:RELIANCE" in k else None

    result = cache.get("RELIANCE")
    assert result == {"ltp": 150.0}
    assert cache._local_cache["RELIANCE"] == {"ltp": 150.0}

def test_cache_get_miss_redis_hit_local(cache):
    # Redis is not available, but local cache has it
    cache._cache.is_available.return_value = False
    cache._local_cache["RELIANCE"] = {"ltp": 100.0}

    result = cache.get("RELIANCE")
    assert result == {"ltp": 100.0}

def test_cache_get_redis_error_fallback(cache):
    # Redis throws exception, falls back to local cache
    cache._cache.is_available.return_value = True
    cache._cache.get.side_effect = Exception("Redis connection refused")
    cache._local_cache["RELIANCE"] = {"ltp": 120.0}

    result = cache.get("RELIANCE")
    assert result == {"ltp": 120.0}

def test_cache_set_ttl_open(cache):
    # Market status is OPEN -> TTL should be 10s
    cache._cache.is_available.return_value = True
    cache._status_service.get_status.return_value = MarketStatus.OPEN
    price_data = {"ltp": 150.0}

    success = cache.set("RELIANCE", price_data)
    assert success is True
    assert cache._local_cache["RELIANCE"] == price_data
    # Verify set was called with TTL=10 for both keys
    cache._cache.set.assert_any_call("price:RELIANCE", price_data, ttl=10)
    cache._cache.set.assert_any_call("qai:tick:RELIANCE", price_data, ttl=10)

def test_cache_set_ttl_closed(cache):
    # Market status is CLOSED -> TTL should be 18000s (5 hours)
    cache._cache.is_available.return_value = True
    cache._status_service.get_status.return_value = MarketStatus.CLOSED
    price_data = {"ltp": 150.0}

    success = cache.set("RELIANCE", price_data)
    assert success is True
    cache._cache.set.assert_any_call("price:RELIANCE", price_data, ttl=18000)

def test_cache_set_ttl_default(cache):
    # Market status is PRE_OPEN -> TTL should be 300s (5 minutes)
    cache._cache.is_available.return_value = True
    cache._status_service.get_status.return_value = MarketStatus.PRE_OPEN
    price_data = {"ltp": 150.0}

    success = cache.set("RELIANCE", price_data)
    assert success is True
    cache._cache.set.assert_any_call("price:RELIANCE", price_data, ttl=300)

def test_cache_clear(cache):
    # Clear cache should delete local and redis keys
    cache._cache.is_available.return_value = True
    cache._local_cache["RELIANCE"] = {"ltp": 150.0}

    cache.clear("RELIANCE")
    assert "RELIANCE" not in cache._local_cache
    cache._cache.delete.assert_any_call("price:RELIANCE")
    cache._cache.delete.assert_any_call("qai:tick:RELIANCE")

def test_cache_set_exception(cache):
    cache._cache.is_available.return_value = True
    cache._status_service.get_status.return_value = MarketStatus.OPEN
    cache._cache.set.side_effect = Exception("Redis connection timed out")
    
    price_data = {"ltp": 150.0}
    success = cache.set("RELIANCE", price_data)
    assert success is False

def test_price_cache_singleton():
    from services.price_manager.price_cache import get_price_cache
    c1 = get_price_cache()
    c2 = get_price_cache()
    assert c1 is c2

