import pytz
from datetime import datetime
from typing import Any

IST = pytz.timezone('Asia/Kolkata')

class PriceFormatter:
    """
    Formats stock price DTO and response fields consistently.
    Rounds currency values and percentages to 2 decimal points.
    """

    def round_field(self, val: Any) -> float:
        try:
            return round(float(val or 0.0), 2)
        except (ValueError, TypeError):
            return 0.0

    def format_timestamp(self, ts: Any) -> str:
        """Standardize all timestamps to ISO 8601 IST string format."""
        try:
            if not ts:
                return datetime.now(IST).isoformat()
            if isinstance(ts, datetime):
                if ts.tzinfo is None:
                    ts = IST.localize(ts)
                return ts.isoformat()
            if isinstance(ts, (int, float)):
                return datetime.fromtimestamp(ts / 1000.0, IST).isoformat()
            # Try to parse ISO format string
            ts_parsed = datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
            if ts_parsed.tzinfo is not None:
                return ts_parsed.astimezone(IST).isoformat()
            return IST.localize(ts_parsed).isoformat()
        except Exception:
            return datetime.now(IST).isoformat()

_price_formatter = None

def get_price_formatter() -> PriceFormatter:
    global _price_formatter
    if _price_formatter is None:
        _price_formatter = PriceFormatter()
    return _price_formatter
