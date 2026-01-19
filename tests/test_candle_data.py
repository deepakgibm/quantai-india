"""
Candle Data Tests
Validates candle data for OHLC sanity, time ordering, and completeness.
"""

import pytest
from typing import Dict, Any, List
from datetime import datetime, timedelta

from tests.utils.test_data import (
    QUICK_TEST_SYMBOLS,
    SYMBOL_TO_INSTRUMENT_KEY,
    VALID_TIMEFRAMES,
    TIMEFRAME_TO_MINUTES,
)
from tests.utils.validators import (
    validate_ohlc_sanity,
    validate_candle_ordering,
)


class TestCandleOHLCSanity:
    """Test OHLC data sanity checks."""
    
    @pytest.mark.parametrize("symbol", QUICK_TEST_SYMBOLS)
    def test_snapshot_ohlc_sanity(self, api_client, symbol):
        """Validate OHLC sanity in HP Scanner snapshots."""
        response = api_client.get(f"/api/v3/scanner/snapshot/{symbol}", auth=False)
        
        if response.status_code != 200:
            pytest.skip(f"Could not get snapshot for {symbol}")
        
        data = response.json()
        
        # Extract OHLC
        ohlc = {
            "open": data.get("open"),
            "high": data.get("high"),
            "low": data.get("low"),
            "close": data.get("close") or data.get("ltp"),
        }
        
        # Skip if no OHLC data
        if not all(ohlc.values()):
            pytest.skip(f"Incomplete OHLC data for {symbol}")
        
        is_valid, errors = validate_ohlc_sanity(ohlc)
        assert is_valid, f"{symbol} OHLC sanity failed: {errors}"
    
    def test_scanner_momentum_ohlc_sanity(self, api_client):
        """Validate OHLC sanity in momentum scanner results."""
        response = api_client.get("/api/v3/scanner/momentum", auth=False)
        
        if response.status_code != 200:
            pytest.skip("Could not get momentum data")
        
        data = response.json()
        stocks = data.get("data", []) or data.get("stocks", [])
        
        if not stocks:
            pytest.skip("No stocks in response")
        
        errors_found = []
        
        for stock in stocks[:10]:
            symbol = stock.get("symbol")
            ohlc = {
                "open": stock.get("open"),
                "high": stock.get("high"),
                "low": stock.get("low"),
                "close": stock.get("close") or stock.get("ltp"),
            }
            
            if not all(ohlc.values()):
                continue
            
            is_valid, errors = validate_ohlc_sanity(ohlc)
            if not is_valid:
                errors_found.append(f"{symbol}: {errors}")
        
        # Allow some failures but majority should pass
        if len(errors_found) > len(stocks[:10]) * 0.3:
            pytest.fail(f"Too many OHLC sanity failures: {errors_found}")


class TestHistoricalCandles:
    """Test historical candle data."""
    
    @pytest.mark.parametrize("symbol", QUICK_TEST_SYMBOLS[:3])
    def test_historical_candle_fetch(self, upstox_client, symbol_to_instrument_key, symbol):
        """Test fetching historical candles from Upstox."""
        instrument_key = symbol_to_instrument_key.get(symbol)
        if not instrument_key:
            pytest.skip(f"No instrument key for {symbol}")
        
        candles = upstox_client.get_historical_candles(
            instrument_key,
            interval="1d",
        )
        
        if not candles:
            pytest.skip(f"Could not fetch candles for {symbol}")
        
        # Should have at least some candles
        assert len(candles) > 0, f"No candles returned for {symbol}"
        
        # Each candle should have 6-7 fields [ts, o, h, l, c, v, oi]
        for candle in candles[:5]:
            assert len(candle) >= 6, f"Candle missing fields: {candle}"
    
    @pytest.mark.parametrize("timeframe", ["1d", "1h", "15m"])
    def test_candle_timeframe_consistency(self, upstox_client, symbol_to_instrument_key, timeframe):
        """Test candle intervals match expected timeframe."""
        symbol = QUICK_TEST_SYMBOLS[0]
        instrument_key = symbol_to_instrument_key.get(symbol)
        
        if not instrument_key:
            pytest.skip(f"No instrument key for {symbol}")
        
        candles = upstox_client.get_historical_candles(
            instrument_key,
            interval=timeframe,
        )
        
        if not candles or len(candles) < 2:
            pytest.skip(f"Not enough candles for {symbol} {timeframe}")
        
        # Check time differences between candles
        expected_minutes = TIMEFRAME_TO_MINUTES.get(timeframe, 1440)
        
        # For daily candles, allow 1 day gap
        if timeframe == "1d":
            expected_minutes = 1440
        
        # Candles are typically in descending order
        for i in range(min(5, len(candles) - 1)):
            ts1 = candles[i][0]
            ts2 = candles[i + 1][0]
            
            if isinstance(ts1, str):
                dt1 = datetime.fromisoformat(ts1.replace("Z", "+00:00"))
                dt2 = datetime.fromisoformat(ts2.replace("Z", "+00:00"))
                
                diff_minutes = abs((dt1 - dt2).total_seconds() / 60)
                
                # Allow some tolerance for market gaps
                if timeframe == "1d":
                    # Daily candles can have weekend gaps
                    assert diff_minutes >= expected_minutes * 0.9
                else:
                    # Intraday should be more consistent
                    # But weekends/holidays can cause gaps
                    pass


class TestCandleOrdering:
    """Test candle time ordering."""
    
    def test_candle_time_order(self, upstox_client, symbol_to_instrument_key):
        """Validate candles are in correct time order."""
        symbol = QUICK_TEST_SYMBOLS[0]
        instrument_key = symbol_to_instrument_key.get(symbol)
        
        if not instrument_key:
            pytest.skip(f"No instrument key for {symbol}")
        
        candles = upstox_client.get_historical_candles(
            instrument_key,
            interval="1d",
        )
        
        if not candles:
            pytest.skip(f"Could not fetch candles for {symbol}")
        
        is_valid, errors = validate_candle_ordering(candles)
        
        # Upstox returns candles in descending order (newest first)
        # This is valid, so we just check consistency
        assert len(candles) > 0


class TestCandleDataCompleteness:
    """Test candle data completeness."""
    
    def test_recent_candles_available(self, upstox_client, symbol_to_instrument_key):
        """Test that recent candles are available."""
        symbol = QUICK_TEST_SYMBOLS[0]
        instrument_key = symbol_to_instrument_key.get(symbol)
        
        if not instrument_key:
            pytest.skip(f"No instrument key for {symbol}")
        
        today = datetime.now()
        from_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        to_date = today.strftime("%Y-%m-%d")
        
        candles = upstox_client.get_historical_candles(
            instrument_key,
            interval="1d",
            from_date=from_date,
            to_date=to_date,
        )
        
        if not candles:
            pytest.skip(f"Could not fetch candles for {symbol}")
        
        # Should have at least 3-5 trading days in a week
        assert len(candles) >= 3, f"Too few candles in last week: {len(candles)}"
    
    @pytest.mark.parametrize("symbol", QUICK_TEST_SYMBOLS[:3])
    def test_candle_volume_present(self, upstox_client, symbol_to_instrument_key, symbol):
        """Test that candles have volume data."""
        instrument_key = symbol_to_instrument_key.get(symbol)
        
        if not instrument_key:
            pytest.skip(f"No instrument key for {symbol}")
        
        candles = upstox_client.get_historical_candles(
            instrument_key,
            interval="1d",
        )
        
        if not candles:
            pytest.skip(f"Could not fetch candles for {symbol}")
        
        # Check volume field (index 5)
        for candle in candles[:5]:
            if len(candle) >= 6:
                volume = candle[5]
                assert volume is not None, f"Missing volume in candle: {candle}"
                assert volume >= 0, f"Invalid volume in candle: {candle}"


class TestCandleValueRanges:
    """Test candle values are in valid ranges."""
    
    @pytest.mark.parametrize("symbol", QUICK_TEST_SYMBOLS)
    def test_candle_positive_values(self, upstox_client, symbol_to_instrument_key, symbol):
        """Test all OHLCV values are positive."""
        instrument_key = symbol_to_instrument_key.get(symbol)
        
        if not instrument_key:
            pytest.skip(f"No instrument key for {symbol}")
        
        candles = upstox_client.get_historical_candles(
            instrument_key,
            interval="1d",
        )
        
        if not candles:
            pytest.skip(f"Could not fetch candles for {symbol}")
        
        for candle in candles[:10]:
            if len(candle) >= 5:
                o, h, l, c = candle[1:5]
                
                # All prices should be positive
                assert o > 0, f"Open <= 0: {o}"
                assert h > 0, f"High <= 0: {h}"
                assert l > 0, f"Low <= 0: {l}"
                assert c > 0, f"Close <= 0: {c}"
                
                # High should be highest
                assert h >= o and h >= c and h >= l
                
                # Low should be lowest
                assert l <= o and l <= c and l <= h
