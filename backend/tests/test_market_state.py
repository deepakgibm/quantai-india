import pytest
from datetime import datetime, date
from unittest.mock import patch

from backend.utils.market_state import is_market_open, get_trading_date, get_market_status, IST

def test_market_open_regular_hours():
    # Mock a regular trading day (e.g., Monday 2024-05-06 10:30 IST)
    mock_now = IST.localize(datetime(2024, 5, 6, 10, 30))
    with patch("backend.utils.market_state.datetime") as mock_dt:
        mock_dt.now.return_value = mock_now
        
        assert is_market_open() == True
        assert get_trading_date() == date(2024, 5, 6)
        
        status = get_market_status()
        assert status["status"] == "OPEN"

def test_market_closed_after_hours():
    # Mock a regular trading day (e.g., Monday 2024-05-06 16:30 IST)
    mock_now = IST.localize(datetime(2024, 5, 6, 16, 30))
    with patch("backend.utils.market_state.datetime") as mock_dt:
        mock_dt.now.return_value = mock_now
        
        assert is_market_open() == False
        assert get_trading_date() == date(2024, 5, 6)
        
        status = get_market_status()
        assert status["status"] == "CLOSED"

def test_market_weekend():
    # Mock a weekend (Saturday 2024-05-11 10:30 IST)
    mock_now = IST.localize(datetime(2024, 5, 11, 10, 30))
    with patch("backend.utils.market_state.datetime") as mock_dt:
        mock_dt.now.return_value = mock_now
        
        assert is_market_open() == False
        # Should return previous trading session (Friday 2024-05-10)
        assert get_trading_date() == date(2024, 5, 10)
        
        status = get_market_status()
        assert status["status"] == "WEEKEND"

def test_market_holiday():
    # Mock a known holiday (e.g., Republic Day 2024-01-26 10:30 IST - Friday)
    mock_now = IST.localize(datetime(2024, 1, 26, 10, 30))
    with patch("backend.utils.market_state.datetime") as mock_dt:
        mock_dt.now.return_value = mock_now
        
        assert is_market_open() == False
        # Should return Thursday 2024-01-25
        assert get_trading_date() == date(2024, 1, 25)
        
        status = get_market_status()
        assert status["status"] == "HOLIDAY"
