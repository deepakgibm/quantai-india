"""
Instrument Resolution Service

Centralized service for resolving symbol/instrument_key to instrument_id.
Implements caching for performance - never queries instrument_master repeatedly per request.
"""

import logging
from typing import Optional, Dict, NamedTuple
from datetime import datetime, timedelta
import psycopg2
from config import settings
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class InstrumentInfo(NamedTuple):
    """Instrument information from instrument_master."""
    instrument_id: int
    instrument_key: str
    symbol: str
    series: str
    exchange: str
    company_name: str
    sector: str
    is_active: bool


# In-memory cache with TTL tracking
_cache: Dict[str, tuple] = {}  # key -> (InstrumentInfo, expiry_time)
_CACHE_TTL_SECONDS = 300  # 5 minutes


def _get_connection():
    """Get database connection."""
    try:
        result = urlparse(settings.DATABASE_URL.replace("+asyncpg", ""))
        return psycopg2.connect(
            host=result.hostname or 'localhost',
            port=result.port or 5432,
            user=result.username or 'postgres',
            password=result.password or 'admin',
            database=result.path.lstrip('/') or 'quantai'
        )
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None


def _is_cache_valid(key: str) -> bool:
    """Check if cache entry is still valid."""
    if key not in _cache:
        return False
    _, expiry = _cache[key]
    return datetime.now() < expiry


def _set_cache(key: str, value: Optional[InstrumentInfo]):
    """Set cache entry with TTL."""
    expiry = datetime.now() + timedelta(seconds=_CACHE_TTL_SECONDS)
    _cache[key] = (value, expiry)


def _get_cache(key: str) -> Optional[InstrumentInfo]:
    """Get cache entry if valid."""
    if _is_cache_valid(key):
        return _cache[key][0]
    return None


def resolve_instrument_id(
    symbol: str,
    series: str = 'EQ',
    exchange: str = 'NSE'
) -> Optional[int]:
    """
    Resolve symbol + series + exchange to instrument_id.
    
    Args:
        symbol: Stock symbol (e.g., 'RELIANCE')
        series: Series type (default: 'EQ')
        exchange: Exchange (default: 'NSE')
    
    Returns:
        instrument_id if found and active, None otherwise
    
    Raises:
        ValueError: If instrument is inactive
    """
    symbol_upper = symbol.upper().strip()
    if symbol_upper in ("NIFTY", "NIFTY_50", "NSE:NIFTY"):
        symbol = "NIFTY 50"

    cache_key = f"sym:{symbol}:{series}:{exchange}"
    
    # Check cache first
    cached = _get_cache(cache_key)
    if cached is not None:
        if not cached.is_active:
            raise ValueError(f"Instrument {symbol} is inactive")
        return cached.instrument_id
    
    # Query database
    conn = _get_connection()
    if not conn:
        logger.error("Could not connect to database for instrument resolution")
        return None
    
    try:
        cursor = conn.cursor()
        if symbol == "NIFTY 50":
            cursor.execute("""
                SELECT 
                    instrument_id, instrument_key, symbol, series, exchange,
                    company_name, sector, is_active
                FROM instrument_master
                WHERE symbol = %s AND exchange = %s
                LIMIT 1
            """, (symbol, exchange))
        else:
            cursor.execute("""
                SELECT 
                    instrument_id, instrument_key, symbol, series, exchange,
                    company_name, sector, is_active
                FROM instrument_master
                WHERE symbol = %s AND series = %s AND exchange = %s
            """, (symbol, series, exchange))
        
        row = cursor.fetchone()
        if not row:
            logger.warning(f"Instrument not found: {symbol}/{series}/{exchange}")
            _set_cache(cache_key, None)
            return None
        
        info = InstrumentInfo(
            instrument_id=row[0],
            instrument_key=row[1],
            symbol=row[2],
            series=row[3],
            exchange=row[4],
            company_name=row[5],
            sector=row[6],
            is_active=row[7]
        )
        
        _set_cache(cache_key, info)
        
        # Also cache by instrument_key for cross-lookup
        _set_cache(f"ikey:{info.instrument_key}", info)
        
        if not info.is_active:
            raise ValueError(f"Instrument {symbol} is inactive")
        
        return info.instrument_id
        
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Error resolving instrument {symbol}: {e}")
        return None
    finally:
        conn.close()


def resolve_instrument_info(
    symbol: str,
    series: str = 'EQ',
    exchange: str = 'NSE'
) -> Optional[InstrumentInfo]:
    """Resolve symbol + series + exchange to full InstrumentInfo using cache."""
    cache_key = f"sym:{symbol}:{series}:{exchange}"
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached
        
    try:
        resolve_instrument_id(symbol, series, exchange)
    except Exception:
        pass
    return _get_cache(cache_key)


def resolve_instrument_key(
    symbol: str,
    series: str = 'EQ',
    exchange: str = 'NSE'
) -> Optional[str]:
    """Resolve symbol + series + exchange to instrument_key using cache."""
    info = resolve_instrument_info(symbol, series, exchange)
    return info.instrument_key if info else None


def resolve_by_instrument_key(instrument_key: str) -> Optional[int]:
    """
    Resolve instrument_key to instrument_id.
    
    Args:
        instrument_key: Upstox instrument key (e.g., 'NSE_EQ|INE002A01018')
    
    Returns:
        instrument_id if found and active, None otherwise
    """
    cache_key = f"ikey:{instrument_key}"
    
    # Check cache first
    cached = _get_cache(cache_key)
    if cached is not None:
        if not cached.is_active:
            logger.warning(f"Instrument {instrument_key} is inactive")
            return None
        return cached.instrument_id
    
    # Query database
    conn = _get_connection()
    if not conn:
        logger.error("Could not connect to database for instrument resolution")
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                instrument_id, instrument_key, symbol, series, exchange,
                company_name, sector, is_active
            FROM instrument_master
            WHERE instrument_key = %s
        """, (instrument_key,))
        
        row = cursor.fetchone()
        if not row:
            logger.warning(f"Instrument not found by key: {instrument_key}")
            _set_cache(cache_key, None)
            return None
        
        info = InstrumentInfo(
            instrument_id=row[0],
            instrument_key=row[1],
            symbol=row[2],
            series=row[3],
            exchange=row[4],
            company_name=row[5],
            sector=row[6],
            is_active=row[7]
        )
        
        _set_cache(cache_key, info)
        
        # Also cache by symbol for cross-lookup
        _set_cache(f"sym:{info.symbol}:{info.series}:{info.exchange}", info)
        
        if not info.is_active:
            logger.warning(f"Instrument {instrument_key} is inactive")
            return None
        
        return info.instrument_id
        
    except Exception as e:
        logger.error(f"Error resolving instrument key {instrument_key}: {e}")
        return None
    finally:
        conn.close()


def get_instrument_info(instrument_id: int) -> Optional[InstrumentInfo]:
    """
    Get full instrument info by instrument_id.
    
    Args:
        instrument_id: The instrument_id to look up
    
    Returns:
        InstrumentInfo if found, None otherwise
    """
    cache_key = f"id:{instrument_id}"
    
    # Check cache first
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached
    
    # Query database
    conn = _get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                instrument_id, instrument_key, symbol, series, exchange,
                company_name, sector, is_active
            FROM instrument_master
            WHERE instrument_id = %s
        """, (instrument_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        info = InstrumentInfo(
            instrument_id=row[0],
            instrument_key=row[1],
            symbol=row[2],
            series=row[3],
            exchange=row[4],
            company_name=row[5],
            sector=row[6],
            is_active=row[7]
        )
        
        _set_cache(cache_key, info)
        return info
        
    except Exception as e:
        logger.error(f"Error getting instrument info for {instrument_id}: {e}")
        return None
    finally:
        conn.close()


def get_symbol_for_instrument_id(instrument_id: int) -> Optional[str]:
    """
    Get symbol for an instrument_id (for API response backward compatibility).
    
    Args:
        instrument_id: The instrument_id to look up
    
    Returns:
        Symbol string if found, None otherwise
    """
    info = get_instrument_info(instrument_id)
    return info.symbol if info else None


def clear_cache():
    """Clear the instrument resolution cache."""
    global _cache
    _cache = {}
    logger.info("Instrument resolution cache cleared")


def warm_cache(limit: int = 500):
    """
    Pre-warm the cache with active instruments.
    Call this at application startup for better performance.
    
    Args:
        limit: Maximum number of instruments to cache
    """
    conn = _get_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                instrument_id, instrument_key, symbol, series, exchange,
                company_name, sector, is_active
            FROM instrument_master
            WHERE is_active = TRUE
            LIMIT %s
        """, (limit,))
        
        count = 0
        for row in cursor.fetchall():
            info = InstrumentInfo(
                instrument_id=row[0],
                instrument_key=row[1],
                symbol=row[2],
                series=row[3],
                exchange=row[4],
                company_name=row[5],
                sector=row[6],
                is_active=row[7]
            )
            
            _set_cache(f"id:{info.instrument_id}", info)
            _set_cache(f"ikey:{info.instrument_key}", info)
            _set_cache(f"sym:{info.symbol}:{info.series}:{info.exchange}", info)
            count += 1
        
        logger.info(f"Instrument cache warmed with {count} instruments")
        
    except Exception as e:
        logger.error(f"Error warming instrument cache: {e}")
    finally:
        conn.close()
