from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
from typing import Optional, Any

class PriceSource(Enum):
    UPSTOX_WS = "UPSTOX_WS"
    UPSTOX_REST = "UPSTOX_REST"
    UPSTOX_REST_FALLBACK = "UPSTOX_REST_FALLBACK"
    DB_EOD = "DB_EOD"
    NONE = "NONE"

class MarketStatus(Enum):
    PRE_OPEN = "PRE_OPEN"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    HOLIDAY = "HOLIDAY"
    WEEKEND = "WEEKEND"
    AFTER_MARKET = "AFTER_MARKET"

@dataclass
class StockPrice:
    symbol: str
    instrument_key: Optional[str]
    ltp: float
    open: float
    high: float
    low: float
    close: float
    previous_close: float
    change: float
    change_percent: float
    volume: int
    timestamp: str  # ISO-8601 string
    market_status: str  # PRE_OPEN, OPEN, etc.
    source: str  # PriceSource value
    last_updated: str  # ISO-8601 string

    def to_dict(self) -> dict:
        return asdict(self)
