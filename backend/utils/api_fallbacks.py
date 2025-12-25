"""
API Fallback Utilities
Provides fallback responses and timeout handling for slow endpoints
"""

import asyncio
from typing import Any, Callable, TypeVar
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


async def with_timeout(coro, timeout_seconds: float = 10.0, fallback: Any = None):
    """Execute coroutine with timeout, return fallback on timeout"""
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.warning(f"Operation timed out after {timeout_seconds}s, using fallback")
        return fallback
    except Exception as e:
        logger.error(f"Operation failed: {e}, using fallback")
        return fallback


def timeout_fallback(timeout: float = 10.0, fallback_func: Callable = None):
    """Decorator for async functions with timeout and fallback"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"{func.__name__} timed out after {timeout}s")
                if fallback_func:
                    return fallback_func(*args, **kwargs)
                return {"status": "timeout", "message": f"Operation timed out after {timeout}s"}
            except Exception as e:
                logger.error(f"{func.__name__} failed: {e}")
                if fallback_func:
                    return fallback_func(*args, **kwargs)
                return {"status": "error", "message": str(e)}
        return wrapper
    return decorator


# Common fallback data
FALLBACK_MARKET_INDICES = [
    {"name": "NIFTY 50", "value": 23850.15, "change": 125.4, "percent": 0.53, "source": "fallback"},
    {"name": "BANK NIFTY", "value": 51200.80, "change": -89.3, "percent": -0.17, "source": "fallback"},
    {"name": "INDIA VIX", "value": 13.25, "change": -0.35, "percent": -2.58, "source": "fallback"}
]

FALLBACK_GAINERS_LOSERS = [
    {"ticker": "RELIANCE", "change": 1.2, "color": "bg-green-500", "price": 2850.0},
    {"ticker": "HDFCBANK", "change": -0.8, "color": "bg-red-400", "price": 1680.0},
    {"ticker": "INFOSYS", "change": 2.1, "color": "bg-green-600", "price": 1545.0},
    {"ticker": "TATASTEEL", "change": 0.5, "color": "bg-green-400", "price": 145.0},
    {"ticker": "SBIN", "change": -1.2, "color": "bg-red-500", "price": 815.0},
    {"ticker": "BAJFINANCE", "change": 0.2, "color": "bg-green-300", "price": 7200.0}
]

FALLBACK_SECTOR_HEATMAP = {
    "status": "success",
    "data": [
        {"sector": "IT", "last_price": 36500, "change_pct": 1.2, "is_bullish": True},
        {"sector": "Banking", "last_price": 51200, "change_pct": 0.8, "is_bullish": True},
        {"sector": "Auto", "last_price": 18900, "change_pct": -0.5, "is_bullish": False},
        {"sector": "Pharma", "last_price": 18200, "change_pct": 0.3, "is_bullish": True},
        {"sector": "FMCG", "last_price": 56800, "change_pct": -0.2, "is_bullish": False},
        {"sector": "Metal", "last_price": 8500, "change_pct": 1.5, "is_bullish": True},
        {"sector": "Realty", "last_price": 1050, "change_pct": 2.1, "is_bullish": True},
        {"sector": "Energy", "last_price": 36200, "change_pct": -0.8, "is_bullish": False},
    ],
    "market_outlook": {
        "verdict": "Neutral",
        "nifty_change": 0.25,
        "suggestion": "Range-bound: Trade with caution",
        "timestamp": "2024-12-24T12:00:00"
    }
}

FALLBACK_STRATEGIES = {
    "status": "success",
    "strategies": {
        "Tier 1 - Highest Win Rate": [
            {"name": "RSI Mean Reversion", "description": "Identifies oversold/overbought conditions using RSI", "tier": "Tier 1 - Highest Win Rate", "min_bars": 30},
            {"name": "Bollinger Breakout", "description": "Detects price breakouts from Bollinger Bands", "tier": "Tier 1 - Highest Win Rate", "min_bars": 20},
            {"name": "Williams %R", "description": "Momentum indicator for overbought/oversold", "tier": "Tier 1 - Highest Win Rate", "min_bars": 14}
        ],
        "Tier 2 - Solid Strategies": [
            {"name": "MACD Crossover", "description": "Classic MACD signal line crossover", "tier": "Tier 2 - Solid Strategies", "min_bars": 26},
            {"name": "ADX Trend", "description": "Trend strength indicator", "tier": "Tier 2 - Solid Strategies", "min_bars": 14},
            {"name": "Stochastic Oscillator", "description": "Momentum comparison indicator", "tier": "Tier 2 - Solid Strategies", "min_bars": 14}
        ],
        "Tier 3 - Advanced Strategies": [
            {"name": "Ichimoku Cloud", "description": "Multi-component trend indicator", "tier": "Tier 3 - Advanced Strategies", "min_bars": 52},
            {"name": "Fibonacci Bounce", "description": "Price reactions at Fibonacci levels", "tier": "Tier 3 - Advanced Strategies", "min_bars": 50}
        ],
        "Multi-Timeframe Confluence": []
    },
    "total_count": 8
}

FALLBACK_INDICES_LIST = {
    "status": "success",
    "indices": [
        {"name": "NIFTY 50", "symbol": "^NSEI", "count": 50},
        {"name": "NIFTY 100", "symbol": "^NSE100", "count": 100},
        {"name": "NIFTY 200", "symbol": "^NSE200", "count": 200},
        {"name": "NIFTY 500", "symbol": "^NSE500", "count": 500}
    ]
}

FALLBACK_ALPHA_SIGNALS = []

FALLBACK_ALPHA_CONFIG = {
    "lookback_days": 30,
    "n_estimators": 100,
    "max_depth": 10,
    "min_confidence": 0.7,
    "status": "not_configured"
}
