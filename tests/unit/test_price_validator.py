import pytest
import math
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from services.price_manager.price_validator import PriceValidator

@pytest.fixture
def validator():
    return PriceValidator()

def test_validate_price_dict_success(validator):
    # Standard successful validation
    data = {
        "ltp": 150.0,
        "prev_close": 148.0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    assert validator.validate_price_dict("RELIANCE", data) is True

def test_validate_price_dict_null_inputs(validator):
    # None inputs
    assert validator.validate_price_dict(None, {"ltp": 100}) is False
    assert validator.validate_price_dict("RELIANCE", None) is False
    assert validator.validate_price_dict("RELIANCE", {}) is False

def test_validate_price_dict_missing_fields(validator):
    # Missing fields
    assert validator.validate_price_dict("RELIANCE", {"ltp": 100}) is False
    assert validator.validate_price_dict("RELIANCE", {"prev_close": 100}) is False

def test_validate_price_dict_invalid_datatypes(validator):
    # Incorrect datatypes
    assert validator.validate_price_dict("RELIANCE", {"ltp": "abc", "prev_close": 100}) is False
    assert validator.validate_price_dict("RELIANCE", {"ltp": 100, "prev_close": "xyz"}) is False
    
    # Coercible datatypes should pass
    data_coercible = {
        "ltp": "150.50",
        "prev_close": 148,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    assert validator.validate_price_dict("RELIANCE", data_coercible) is True

def test_validate_price_dict_nan_inf(validator):
    # NaN and Inf checks
    assert validator.validate_price_dict("RELIANCE", {"ltp": float('nan'), "prev_close": 100}) is False
    assert validator.validate_price_dict("RELIANCE", {"ltp": 100, "prev_close": float('nan')}) is False
    assert validator.validate_price_dict("RELIANCE", {"ltp": float('inf'), "prev_close": 100}) is False
    assert validator.validate_price_dict("RELIANCE", {"ltp": 100, "prev_close": float('-inf')}) is False

def test_validate_price_dict_negative_or_zero(validator):
    # Negative and Zero values
    assert validator.validate_price_dict("RELIANCE", {"ltp": -10.0, "prev_close": 100}) is False
    assert validator.validate_price_dict("RELIANCE", {"ltp": 0.0, "prev_close": 100}) is False
    assert validator.validate_price_dict("RELIANCE", {"ltp": 100.0, "prev_close": -5.0}) is False
    assert validator.validate_price_dict("RELIANCE", {"ltp": 100.0, "prev_close": 0.0}) is False

def test_validate_price_dict_circuit_limit(validator):
    # Circuit breaches (> 21% change)
    # 100 -> 121 (exactly 21%) should pass
    assert validator.validate_price_dict("RELIANCE", {"ltp": 121.0, "prev_close": 100.0}) is True
    # 100 -> 122 (22%) should fail
    assert validator.validate_price_dict("RELIANCE", {"ltp": 122.0, "prev_close": 100.0}) is False
    # 100 -> 78 (22% drop) should fail
    assert validator.validate_price_dict("RELIANCE", {"ltp": 78.0, "prev_close": 100.0}) is False

@patch('services.price_manager.market_status_service.MarketStatusService.is_live_session')
def test_validate_price_dict_freshness(mock_is_live, validator):
    # Freshness Check (Only during live trading sessions)
    mock_is_live.return_value = True
    
    # Fresh tick should pass
    fresh_data = {
        "ltp": 100.0,
        "prev_close": 100.0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    assert validator.validate_price_dict("RELIANCE", fresh_data) is True
    
    # Stale tick (> 60s age) should fail
    stale_time = datetime.now(timezone.utc) - timedelta(seconds=61)
    stale_data = {
        "ltp": 100.0,
        "prev_close": 100.0,
        "timestamp": stale_time.isoformat()
    }
    assert validator.validate_price_dict("RELIANCE", stale_data) is False
    
    # Numeric timestamp (epoch ms) support
    epoch_fresh = {
        "ltp": 100.0,
        "prev_close": 100.0,
        "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
    }
    assert validator.validate_price_dict("RELIANCE", epoch_fresh) is True
    
    epoch_stale = {
        "ltp": 100.0,
        "prev_close": 100.0,
        "timestamp": int((datetime.now(timezone.utc) - timedelta(seconds=65)).timestamp() * 1000)
    }
    assert validator.validate_price_dict("RELIANCE", epoch_stale) is False

@patch('services.price_manager.market_status_service.MarketStatusService.is_live_session')
def test_validate_price_dict_not_live_session_ignores_staleness(mock_is_live, validator):
    # Outside live session, stale ticks are allowed
    mock_is_live.return_value = False
    
    stale_time = datetime.now(timezone.utc) - timedelta(days=2)
    stale_data = {
        "ltp": 100.0,
        "prev_close": 100.0,
        "timestamp": stale_time.isoformat()
    }
    assert validator.validate_price_dict("RELIANCE", stale_data) is True

@patch('services.price_manager.market_status_service.MarketStatusService.is_live_session')
def test_validate_price_dict_invalid_timestamp_parsing(mock_is_live, validator):
    mock_is_live.return_value = True
    data = {
        "ltp": 100.0,
        "prev_close": 100.0,
        "timestamp": "not-an-iso-timestamp"
    }
    assert validator.validate_price_dict("RELIANCE", data) is True

def test_validate_price_dict_unexpected_exception(validator):
    class CorruptData:
        def get(self, key, default=None):
            if key == "ltp":
                raise RuntimeError("Unexpected failure")
            return None
    assert validator.validate_price_dict("RELIANCE", CorruptData()) is False

def test_validator_singleton_factory():
    from services.price_manager.price_validator import get_price_validator
    val1 = get_price_validator()
    val2 = get_price_validator()
    assert val1 is val2
