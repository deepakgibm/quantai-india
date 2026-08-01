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


# In-memory dictionaries for static resolution
_instruments_by_id: Dict[int, InstrumentInfo] = {}
_instruments_by_key: Dict[str, InstrumentInfo] = {}
_instruments_by_sym: Dict[str, InstrumentInfo] = {}  # "symbol:series:exchange" -> InstrumentInfo
_is_loaded = False


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


def _load_all_instruments():
    global _is_loaded
    if _is_loaded:
        return
        
    conn = _get_connection()
    if not conn:
        logger.error("Could not connect to database to load instruments")
        return
        
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                instrument_id, instrument_key, symbol, series, exchange,
                company_name, sector, is_active
            FROM instrument_master
        """)
        rows = cursor.fetchall()
        for row in rows:
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
            _instruments_by_id[info.instrument_id] = info
            _instruments_by_key[info.instrument_key.upper()] = info
            
            # Map standard symbol lookup
            _instruments_by_sym[f"{info.symbol.upper()}:{info.series.upper()}:{info.exchange.upper()}"] = info
            
        _is_loaded = True
        logger.info(f"Instrument Resolver: Loaded {len(rows)} instruments in memory.")
    except Exception as e:
        logger.error(f"Error loading instruments from master: {e}")
    finally:
        conn.close()


def resolve_instrument_id(
    symbol: str,
    series: str = 'EQ',
    exchange: str = 'NSE'
) -> Optional[int]:
    """Resolve symbol + series + exchange to instrument_id."""
    _load_all_instruments()
    
    symbol_upper = symbol.upper().strip()
    if symbol_upper in ("NIFTY", "NIFTY_50", "NSE:NIFTY"):
        symbol_upper = "NIFTY 50"
        
    key = f"{symbol_upper}:{series.upper()}:{exchange.upper()}"
    info = _instruments_by_sym.get(key)
    
    if not info:
        logger.warning(f"Instrument not found: {symbol}/{series}/{exchange}")
        return None
        
    if not info.is_active:
        raise ValueError(f"Instrument {symbol} is inactive")
        
    return info.instrument_id


def resolve_instrument_info(
    symbol: str,
    series: str = 'EQ',
    exchange: str = 'NSE'
) -> Optional[InstrumentInfo]:
    """Resolve symbol + series + exchange to full InstrumentInfo."""
    _load_all_instruments()
    
    symbol_upper = symbol.upper().strip()
    if symbol_upper in ("NIFTY", "NIFTY_50", "NSE:NIFTY"):
        symbol_upper = "NIFTY 50"
        
    key = f"{symbol_upper}:{series.upper()}:{exchange.upper()}"
    info = _instruments_by_sym.get(key)
    if info:
        return info
        
    # SRE Fallback: If exact EQ series lookup fails, search for matching symbol with SM, BE, or other series
    prefix = f"{symbol_upper}:"
    for k, val in _instruments_by_sym.items():
        if k.startswith(prefix):
            return val
            
    return None


def resolve_instrument_key(
    symbol: str,
    series: str = 'EQ',
    exchange: str = 'NSE'
) -> Optional[str]:
    """Resolve symbol + series + exchange to instrument_key."""
    info = resolve_instrument_info(symbol, series, exchange)
    return info.instrument_key if info else None


def resolve_by_instrument_key(instrument_key: str) -> Optional[int]:
    """Resolve instrument_key to instrument_id."""
    _load_all_instruments()
    info = _instruments_by_key.get(instrument_key.upper())
    if not info:
        logger.warning(f"Instrument not found by key: {instrument_key}")
        return None
        
    if not info.is_active:
        logger.warning(f"Instrument {instrument_key} is inactive")
        return None
        
    return info.instrument_id


def get_instrument_info(instrument_id: int) -> Optional[InstrumentInfo]:
    """Get full instrument info by instrument_id."""
    _load_all_instruments()
    return _instruments_by_id.get(instrument_id)


def get_symbol_for_instrument_id(instrument_id: int) -> Optional[str]:
    """Get symbol for an instrument_id."""
    info = get_instrument_info(instrument_id)
    return info.symbol if info else None


def clear_cache():
    """Clear the instrument resolution cache."""
    global _is_loaded, _instruments_by_id, _instruments_by_key, _instruments_by_sym
    _instruments_by_id = {}
    _instruments_by_key = {}
    _instruments_by_sym = {}
    _is_loaded = False
    logger.info("Instrument resolution cache cleared")


def warm_cache(limit: int = 500):
    """Pre-warm the cache by loading all instruments."""
    _load_all_instruments()
