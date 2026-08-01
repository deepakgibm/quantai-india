import pytest
import pytz
from datetime import datetime, timezone
from services.price_manager.price_formatter import PriceFormatter

@pytest.fixture
def formatter():
    return PriceFormatter()

def test_round_field(formatter):
    # Floating point rounding
    assert formatter.round_field(123.456) == 123.46
    assert formatter.round_field(123.4) == 123.40
    assert formatter.round_field(123) == 123.00
    
    # None or non-numeric values
    assert formatter.round_field(None) == 0.00
    assert formatter.round_field("abc") == 0.00
    assert formatter.round_field("12.345") == 12.35

def test_format_timestamp_none(formatter):
    # None input should return current time as IST string
    ts_str = formatter.format_timestamp(None)
    assert isinstance(ts_str, str)
    assert "+05:30" in ts_str

def test_format_timestamp_datetime(formatter):
    # Timezone-naive datetime
    dt_naive = datetime(2026, 7, 12, 10, 0, 0)
    ts_str = formatter.format_timestamp(dt_naive)
    assert "2026-07-12T10:00:00+05:30" in ts_str

    # Timezone-aware datetime (UTC)
    dt_utc = datetime(2026, 7, 12, 10, 0, 0, tzinfo=timezone.utc)
    ts_str = formatter.format_timestamp(dt_utc)
    # The production code does not convert tz-aware datetimes to IST. It returns ts.isoformat() directly.
    assert "2026-07-12T10:00:00+00:00" in ts_str

def test_format_timestamp_numeric(formatter):
    # Epoch milliseconds (e.g. 1779558680000)
    ts_str = formatter.format_timestamp(1779558680000)
    assert "+05:30" in ts_str

def test_format_timestamp_string(formatter):
    # ISO string with 'Z'
    ts_str = formatter.format_timestamp("2026-07-12T10:00:00Z")
    assert "2026-07-12T15:30:00+05:30" in ts_str

    # ISO string without timezone (assume local/IST localized)
    ts_str = formatter.format_timestamp("2026-07-12T10:00:00")
    assert "2026-07-12T10:00:00+05:30" in ts_str

    # Invalid timestamp string should fallback to current time
    ts_str = formatter.format_timestamp("invalid-date")
    assert "+05:30" in ts_str
