import pytest
from datetime import datetime, date
import pytz
from unittest.mock import patch, MagicMock
from services.price_manager.market_status_service import MarketStatusService
from services.price_manager.models import MarketStatus
from services.market_hours_service import get_market_hours_service

IST = pytz.timezone('Asia/Kolkata')

@pytest.fixture
def status_service():
    return MarketStatusService()

def test_market_status_weekend(status_service):
    # Mock Saturday
    saturday_dt = IST.localize(datetime(2026, 7, 11, 10, 0, 0))  # Saturday
    with patch.object(get_market_hours_service(), '_get_ist_now', return_value=saturday_dt):
        assert status_service.get_status() == MarketStatus.WEEKEND
        assert status_service.is_live_session() is False

def test_market_status_holiday(status_service):
    # Mock Republic Day (Jan 26th, 2026) which is Monday
    holiday_dt = IST.localize(datetime(2026, 1, 26, 10, 0, 0))
    with patch.object(get_market_hours_service(), '_get_ist_now', return_value=holiday_dt):
        assert status_service.get_status() == MarketStatus.HOLIDAY
        assert status_service.is_live_session() is False

def test_market_status_pre_open(status_service):
    # Mock Monday 09:05 AM IST
    pre_open_dt = IST.localize(datetime(2026, 7, 13, 9, 5, 0))
    with patch.object(get_market_hours_service(), '_get_ist_now', return_value=pre_open_dt):
        assert status_service.get_status() == MarketStatus.PRE_OPEN
        assert status_service.is_live_session() is False

def test_market_status_open(status_service):
    # Mock Monday 10:00 AM IST
    open_dt = IST.localize(datetime(2026, 7, 13, 10, 0, 0))
    with patch.object(get_market_hours_service(), '_get_ist_now', return_value=open_dt):
        assert status_service.get_status() == MarketStatus.OPEN
        assert status_service.is_live_session() is True

def test_market_status_after_market(status_service):
    # Mock Monday 03:45 PM IST
    after_market_dt = IST.localize(datetime(2026, 7, 13, 15, 45, 0))
    with patch.object(get_market_hours_service(), '_get_ist_now', return_value=after_market_dt):
        assert status_service.get_status() == MarketStatus.AFTER_MARKET
        assert status_service.is_live_session() is False

def test_market_status_closed(status_service):
    # Mock Monday 08:00 PM IST
    closed_dt = IST.localize(datetime(2026, 7, 13, 20, 0, 0))
    with patch.object(get_market_hours_service(), '_get_ist_now', return_value=closed_dt):
        assert status_service.get_status() == MarketStatus.CLOSED
        assert status_service.is_live_session() is False
