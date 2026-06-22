"""
Market State Utilities

Centralized helpers for determining market state and
managing snapshot fallback across all API endpoints.
"""

from datetime import datetime, date, timedelta
from typing import Optional, Any, Callable
import logging

import pytz

logger = logging.getLogger(__name__)

IST = pytz.timezone('Asia/Kolkata')


def is_market_open() -> bool:
    """
    Check if Indian stock market (NSE) is currently open.
    
    Market hours: 09:15 - 15:30 IST, Monday-Friday
    Excludes weekends and known holidays.
    
    Returns:
        True if market is open, False otherwise
    """
    now = datetime.now(IST)
    
    # Weekend check
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    # Convert to minutes from midnight for easy comparison
    current_minutes = now.hour * 60 + now.minute
    market_open = 9 * 60 + 15   # 09:15 = 555 minutes
    market_close = 15 * 60 + 30  # 15:30 = 930 minutes
    
    return market_open <= current_minutes <= market_close


def get_trading_date() -> date:
    """
    Get the current trading date.
    
    If weekend, returns last Friday.
    If before market open, returns previous trading day.
    
    Returns:
        The trading date to use for data lookups
    """
    now = datetime.now(IST)
    today = now.date()
    
    # Weekend handling
    if today.weekday() == 5:  # Saturday
        return today - timedelta(days=1)
    elif today.weekday() == 6:  # Sunday
        return today - timedelta(days=2)
    
    # Before market open, use previous day's data
    current_minutes = now.hour * 60 + now.minute
    if current_minutes < 555:  # Before 09:15
        if today.weekday() == 0:  # Monday -> Friday
            return today - timedelta(days=3)
        return today - timedelta(days=1)
    
    return today


def get_snapshot_cache_key(endpoint: str, trade_date: Optional[date] = None) -> str:
    """
    Generate a cache key for endpoint snapshot.
    
    Args:
        endpoint: The endpoint name (e.g., "scanner_momentum", "heatmap_sectors")
        trade_date: Optional trade date, defaults to current trading date
        
    Returns:
        Cache key string
    """
    if trade_date is None:
        trade_date = get_trading_date()
    
    date_str = trade_date.strftime("%Y-%m-%d")
    return f"snapshot:{endpoint}:{date_str}"


async def get_with_snapshot_fallback(
    live_data_fn: Callable[[], Any],
    snapshot_key: str,
    cache,
    timeout: float = 5.0
) -> tuple:
    """
    Get data with automatic snapshot fallback when market is closed.
    
    During market hours:
        - Calls live_data_fn to get real-time data
        
    After market hours:
        - Returns cached snapshot data
        - Falls back to live_data_fn if no snapshot
    
    Args:
        live_data_fn: Async function that returns live data
        snapshot_key: Cache key for snapshot data
        cache: Dragonfly cache instance
        timeout: Timeout for live data fetch
        
    Returns:
        Tuple of (data, source) where source is "live" or "snapshot"
    """
    import asyncio
    
    if is_market_open():
        # Market is open - get live data
        try:
            data = await asyncio.wait_for(live_data_fn(), timeout=timeout)
            return data, "live"
        except asyncio.TimeoutError:
            logger.warning(f"Live data timeout for {snapshot_key}")
        except Exception as e:
            logger.warning(f"Live data error for {snapshot_key}: {e}")
    
    # Market is closed OR live data failed - try snapshot
    try:
        cached = cache.get(snapshot_key)
        if cached:
            logger.info(f"Returning snapshot data for {snapshot_key}")
            return cached, "snapshot"
    except Exception as e:
        logger.warning(f"Snapshot cache read error: {e}")
    
    # No snapshot - fall back to live (may be stale)
    try:
        data = await asyncio.wait_for(live_data_fn(), timeout=timeout)
        return data, "live_fallback"
    except Exception as e:
        logger.error(f"All data sources failed for {snapshot_key}: {e}")
        return None, "error"


def get_market_status() -> dict:
    """
    Get detailed market status information.
    
    Returns:
        Dict with market state details
    """
    now = datetime.now(IST)
    is_open = is_market_open()
    
    current_minutes = now.hour * 60 + now.minute
    market_open = 555   # 09:15
    market_close = 930  # 15:30
    
    if is_open:
        minutes_to_close = market_close - current_minutes
        status = "OPEN"
        next_event = f"Closes in {minutes_to_close} minutes"
    elif now.weekday() >= 5:
        status = "WEEKEND"
        next_event = "Opens Monday 09:15 IST"
    elif current_minutes < market_open:
        minutes_to_open = market_open - current_minutes
        status = "PRE_MARKET"
        next_event = f"Opens in {minutes_to_open} minutes"
    else:
        status = "CLOSED"
        next_event = "Opens tomorrow 09:15 IST"
    
    return {
        "status": status,
        "is_open": is_open,
        "trading_date": str(get_trading_date()),
        "current_time": now.strftime("%H:%M:%S IST"),
        "next_event": next_event
    }
