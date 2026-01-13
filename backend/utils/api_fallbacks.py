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
FALLBACK_MARKET_INDICES = []
FALLBACK_GAINERS_LOSERS = []
FALLBACK_SECTOR_HEATMAP = {
    "status": "success",
    "data": [],
    "market_outlook": {
        "verdict": "Neutral",
        "nifty_change": 0,
        "suggestion": "Data unavailable",
        "timestamp": ""
    }
}

FALLBACK_STRATEGIES = {
    "status": "success",
    "strategies": {},
    "total_count": 0
}

FALLBACK_INDICES_LIST = {
    "status": "success",
    "indices": []
}

FALLBACK_ALPHA_SIGNALS = []

FALLBACK_ALPHA_CONFIG = {
    "lookback_days": 30,
    "n_estimators": 100,
    "max_depth": 10,
    "min_confidence": 0.7,
    "status": "not_configured"
}
