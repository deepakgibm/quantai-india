"""
Test Data Configuration
Contains test symbol sets, API endpoints, and test constants.
"""

from typing import List, Dict, Any

# =============================================================================
# Test Symbols - NIFTY 50 Subset (25 liquid stocks)
# =============================================================================

TEST_SYMBOLS: List[str] = [
    "RELIANCE",
    "TCS", 
    "HDFCBANK",
    "INFY",
    "ICICIBANK",
    "HDFC",
    "SBIN",
    "BHARTIARTL",
    "KOTAKBANK",
    "ITC",
    "LT",
    "AXISBANK",
    "ASIANPAINT",
    "MARUTI",
    "SUNPHARMA",
    "BAJFINANCE",
    "TITAN",
    "NESTLEIND",
    "WIPRO",
    "ULTRACEMCO",
    "TECHM",
    "HCLTECH",
    "POWERGRID",
    "ONGC",
    "NTPC",
]

# Smaller subset for quick tests
QUICK_TEST_SYMBOLS: List[str] = [
    "RELIANCE",
    "TCS",
    "HDFCBANK",
    "INFY",
    "ICICIBANK",
]

# Edge case symbols
EDGE_CASE_SYMBOLS: Dict[str, str] = {
    "invalid": "INVALID_SYMBOL_123",
    "special_chars": "TEST@#$",
    "empty": "",
    "numeric": "12345",
}

# =============================================================================
# Instrument Keys for Upstox API
# =============================================================================

SYMBOL_TO_INSTRUMENT_KEY: Dict[str, str] = {
    "RELIANCE": "NSE_EQ|INE002A01018",
    "TCS": "NSE_EQ|INE467B01029",
    "HDFCBANK": "NSE_EQ|INE040A01034",
    "INFY": "NSE_EQ|INE009A01021",
    "ICICIBANK": "NSE_EQ|INE090A01021",
    "HDFC": "NSE_EQ|INE001A01036",
    "SBIN": "NSE_EQ|INE062A01020",
    "BHARTIARTL": "NSE_EQ|INE397D01024",
    "KOTAKBANK": "NSE_EQ|INE237A01028",
    "ITC": "NSE_EQ|INE154A01025",
    "LT": "NSE_EQ|INE018A01030",
    "AXISBANK": "NSE_EQ|INE238A01034",
    "ASIANPAINT": "NSE_EQ|INE021A01026",
    "MARUTI": "NSE_EQ|INE585B01010",
    "SUNPHARMA": "NSE_EQ|INE044A01036",
    "BAJFINANCE": "NSE_EQ|INE296A01024",
    "TITAN": "NSE_EQ|INE280A01028",
    "NESTLEIND": "NSE_EQ|INE239A01016",
    "WIPRO": "NSE_EQ|INE075A01022",
    "ULTRACEMCO": "NSE_EQ|INE481G01011",
    "TECHM": "NSE_EQ|INE669C01036",
    "HCLTECH": "NSE_EQ|INE860A01027",
    "POWERGRID": "NSE_EQ|INE752E01010",
    "ONGC": "NSE_EQ|INE213A01029",
    "NTPC": "NSE_EQ|INE733E01010",
}

# =============================================================================
# API Endpoints Configuration
# =============================================================================

# Public endpoints (no auth required)
PUBLIC_ENDPOINTS: List[Dict[str, Any]] = [
    {"path": "/", "method": "GET", "expected_status": 200},
    {"path": "/health", "method": "GET", "expected_status": 200},
    {"path": "/ready", "method": "GET", "expected_status": 200},
    {"path": "/api/upstox/status", "method": "GET", "expected_status": 200},
    {"path": "/api/upstox/connect-url", "method": "GET", "expected_status": 200},
    {"path": "/api/market/nifty100/top-movers", "method": "GET", "expected_status": 200},
    {"path": "/api/market/top-movers", "method": "GET", "expected_status": 200},
    {"path": "/api/market/indices", "method": "GET", "expected_status": 200},
    {"path": "/api/trading/health", "method": "GET", "expected_status": 200},
    {"path": "/api/trading/market-indices", "method": "GET", "expected_status": 200},
    {"path": "/api/trading/instruments", "method": "GET", "expected_status": 200},
]

# Authenticated endpoints (auth required)
AUTH_ENDPOINTS: List[Dict[str, Any]] = [
    {"path": "/api/auth/me", "method": "GET", "expected_status": 200},
    {"path": "/api/trading/dashboard", "method": "GET", "expected_status": 200},
    {"path": "/api/trading/top-gainers", "method": "GET", "expected_status": 200},
    {"path": "/api/trading/gainers-losers", "method": "GET", "expected_status": 200},
    {"path": "/api/scanner/strategies", "method": "GET", "expected_status": 200},
    {"path": "/api/scanner/indices", "method": "GET", "expected_status": 200},
    {"path": "/api/scanner/timeframes", "method": "GET", "expected_status": 200},
    {"path": "/api/scanner/momentum", "method": "GET", "expected_status": 200},
    {"path": "/api/scanner/reversal", "method": "GET", "expected_status": 200},
    {"path": "/api/scanner/trendfinder", "method": "GET", "expected_status": 200},
    {"path": "/api/scanner/week52-breakouts", "method": "GET", "expected_status": 200},
    {"path": "/api/scanner/breakout", "method": "GET", "expected_status": 200},
    {"path": "/api/heatmap/sectors", "method": "GET", "expected_status": 200},
    {"path": "/api/ai/strategies", "method": "GET", "expected_status": 200},
    {"path": "/api/algorithms/", "method": "GET", "expected_status": 200},
    {"path": "/api/engines/performance", "method": "GET", "expected_status": 200},
    {"path": "/api/ai/trend-finder", "method": "GET", "expected_status": 200},
    {"path": "/api/ai/breakout-detector", "method": "GET", "expected_status": 200},
    {"path": "/api/ai/breakout-stocks", "method": "GET", "expected_status": 200},
    {"path": "/api/ai/top5-picks", "method": "GET", "expected_status": 200},
    {"path": "/api/ai/momentum-stocks", "method": "GET", "expected_status": 200},
    {"path": "/api/ai/mean-reversion", "method": "GET", "expected_status": 200},
    {"path": "/api/ai/gap-scanner", "method": "GET", "expected_status": 200},
    {"path": "/api/ai/relative-strength", "method": "GET", "expected_status": 200},
    {"path": "/api/ai/vwap-scanner", "method": "GET", "expected_status": 200},
    {"path": "/api/ai/sr-bounce", "method": "GET", "expected_status": 200},
]

# Optional auth endpoints (work with or without auth)
OPTIONAL_AUTH_ENDPOINTS: List[Dict[str, Any]] = []

# HP Scanner v3 endpoints (no auth)
HP_SCANNER_ENDPOINTS: List[Dict[str, Any]] = [
    {"path": "/api/v3/scanner/momentum", "method": "GET", "expected_status": 200},
    {"path": "/api/v3/scanner/breakout", "method": "GET", "expected_status": 200},
    {"path": "/api/v3/scanner/reversal", "method": "GET", "expected_status": 200},
    {"path": "/api/v3/scanner/signals", "method": "GET", "expected_status": 200},
    {"path": "/api/v3/scanner/snapshots", "method": "GET", "expected_status": 200},
    {"path": "/api/v3/scanner/status", "method": "GET", "expected_status": 200},
    {"path": "/api/v3/scanner/metrics", "method": "GET", "expected_status": 200},
]

# Endpoints that return price data
PRICE_DATA_ENDPOINTS: List[Dict[str, Any]] = [
    {
        "path": "/api/market/nifty100/top-movers",
        "method": "GET",
        "price_fields": ["ltp", "change", "change_percent"],
        "data_path": "gainers",  # or "losers"
    },
    {
        "path": "/api/trading/top-gainers",
        "method": "GET",
        "price_fields": ["ltp", "change", "change_percent"],
        "data_path": "gainers",
    },
    {
        "path": "/api/ai/top5-picks",
        "method": "GET",
        "price_fields": ["ltp", "current_price", "price"],
        "data_path": "stocks",
    },
    {
        "path": "/api/ai/breakout-stocks",
        "method": "GET",
        "price_fields": ["ltp", "current_price", "price"],
        "data_path": "stocks",
    },
    {
        "path": "/api/v3/scanner/momentum",
        "method": "GET",
        "price_fields": ["ltp", "price", "close"],
        "data_path": "data",
    },
    {
        "path": "/api/v3/scanner/snapshots",
        "method": "GET",
        "price_fields": ["ltp", "close"],
        "data_path": "snapshots",
    },
]

# =============================================================================
# Timeframes
# =============================================================================

VALID_TIMEFRAMES: List[str] = ["5m", "15m", "30m", "1h", "1d"]

TIMEFRAME_TO_MINUTES: Dict[str, int] = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
}

# =============================================================================
# Tolerance Thresholds
# =============================================================================

# Price comparison tolerances (as decimal percentages)
TOLERANCE_LTP: float = 0.001  # 0.1%
TOLERANCE_OHLC: float = 0.002  # 0.2%
TOLERANCE_VOLUME: float = 0.05  # 5% (volume can vary more)

# Staleness thresholds (in minutes)
STALE_THRESHOLD_LIVE: int = 5  # During market hours
STALE_THRESHOLD_EOD: int = 1440  # After market hours (1 day)

# =============================================================================
# Market Hours (IST)
# =============================================================================

MARKET_OPEN_HOUR: int = 9
MARKET_OPEN_MINUTE: int = 15
MARKET_CLOSE_HOUR: int = 15
MARKET_CLOSE_MINUTE: int = 30
