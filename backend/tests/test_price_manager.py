import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from services.price_manager import (
    get_price_validator,
    get_price_formatter,
    get_price_calculation_engine,
    get_market_status_service,
    get_price_service,
    PriceSource,
    MarketStatus,
    StockPrice
)

def test_price_validator():
    validator = get_price_validator()
    
    # Valid price dict
    valid_data = {
        "ltp": 150.0,
        "prev_close": 148.0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    assert validator.validate_price_dict("RELIANCE", valid_data) is True
    
    # Negative Price
    invalid_neg = {
        "ltp": -10.0,
        "prev_close": 148.0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    assert validator.validate_price_dict("RELIANCE", invalid_neg) is False
    
    # NaN
    invalid_nan = {
        "ltp": float('nan'),
        "prev_close": 148.0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    assert validator.validate_price_dict("RELIANCE", invalid_nan) is False
    
    # Circuit Limit Breach (> 21%)
    invalid_circuit = {
        "ltp": 200.0,
        "prev_close": 100.0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    assert validator.validate_price_dict("RELIANCE", invalid_circuit) is False

def test_price_formatter():
    formatter = get_price_formatter()
    
    assert formatter.round_field(123.456) == 123.46
    assert formatter.round_field(None) == 0.0
    
    # ISO IST parsing
    ist_ts = formatter.format_timestamp("2026-07-12T10:00:00")
    assert "+05:30" in ist_ts

def test_price_calculation_engine():
    calc = get_price_calculation_engine()
    
    assert calc.calculate_change(150.0, 100.0) == 50.0
    assert calc.calculate_change_percent(150.0, 100.0) == 50.0
    assert calc.calculate_change_percent(150.0, 0.0) == 0.0
    assert calc.calculate_gap(105.0, 100.0) == 5.0

def test_market_status_service():
    status_service = get_market_status_service()
    status = status_service.get_status()
    assert isinstance(status, MarketStatus)

@pytest.mark.asyncio
async def test_price_service_deduplication():
    from unittest.mock import patch
    service = get_price_service()
    
    mock_val = {
        "symbol": "RELIANCE",
        "ltp": 150.0,
        "prev_close": 148.0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "price_source": "UPSTOX_WS"
    }
    
    # Use async side_effect with sleep to allow concurrent task scheduling
    async def async_resolve_mock(symbol):
        await asyncio.sleep(0.05)
        return mock_val
        
    with patch.object(service, "_resolve_price_dict", side_effect=async_resolve_mock) as mock_resolve:
        # Concurrent calls to the same symbol
        t1 = service.get_price("RELIANCE")
        t2 = service.get_price("RELIANCE")
        
        res1, res2 = await asyncio.gather(t1, t2)
        
        # Ensure inner method called exactly once due to deduplication
        assert mock_resolve.call_count == 1
        assert res1["ltp"] == 150.0
        assert res2["ltp"] == 150.0
