"""
Index Constituents Configuration Loader
========================================
Database-driven lookup with JSON fallback.
Supports hierarchical index definitions (e.g., NIFTY 100 includes NIFTY 50).

Extended with:
  - get_universe_symbols_with_keys() for scanners that need (symbol, instrument_key)
  - clear_cache() called automatically after every index refresh
"""

import json
import os
import time
from typing import Dict, List, Tuple
import logging
from sqlalchemy import text

# Try to import DB components
try:
    from database import sync_engine
    _DB_AVAILABLE = True
except ImportError:
    _DB_AVAILABLE = False

logger = logging.getLogger(__name__)

# Path to the fallback config file
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'index_constituents.json')

# ---------------------------------------------------------------------------
# Simple in-process TTL cache (5 minutes)
# ---------------------------------------------------------------------------
_cache: Dict[str, Tuple[float, any]] = {}
_CACHE_TTL = 300  # seconds


def _get_cached(key: str):
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < _CACHE_TTL:
        return entry[1]
    return None


def _set_cached(key: str, value):
    _cache[key] = (time.time(), value)


def clear_cache():
    """Clear all in-process index caches. Called after every refresh."""
    _cache.clear()
    logger.info("Index config cache cleared")


# ---------------------------------------------------------------------------
# JSON fallback loader
# ---------------------------------------------------------------------------

def load_index_config() -> Dict:
    """Load index constituents configuration from JSON file."""
    cached = _get_cached("_json_config")
    if cached is not None:
        return cached
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                data = json.load(f)
                _set_cached("_json_config", data)
                return data
    except Exception as e:
        logger.error(f"Failed to load index config JSON: {e}")
    return {}


# ---------------------------------------------------------------------------
# Core public API
# ---------------------------------------------------------------------------

def get_index_constituents(index_name: str) -> List[str]:
    """
    Get constituent symbols for an index.
    Prioritizes Database, falls back to JSON.
    """
    cache_key = f"constituents:{index_name}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    if _DB_AVAILABLE:
        try:
            with sync_engine.connect() as conn:
                # Fetch active constituents directly from index_constituent (no recursive join needed)
                query = text("""
                    SELECT DISTINCT inst.symbol
                    FROM index_master im
                    JOIN index_constituent ic ON ic.index_id = im.index_id
                    JOIN instrument_master inst ON ic.instrument_id = inst.instrument_id
                    WHERE im.index_name = :name
                      AND ic.removed_at IS NULL
                      AND inst.is_active = TRUE
                    ORDER BY inst.symbol
                """)
                result = conn.execute(query, {"name": index_name})
                symbols = [row[0] for row in result]
                if symbols:
                    logger.info(f"Loaded {len(symbols)} symbols for '{index_name}' from DB")
                    _set_cached(cache_key, sorted(symbols))
                    return sorted(symbols)
        except Exception as e:
            logger.warning(f"DB index lookup failed for '{index_name}': {e}. Using JSON fallback.")

    # JSON fallback
    config = load_index_config()
    if index_name not in config:
        return []

    index_data = config[index_name]
    constituents = set(index_data.get('constituents', []))

    base_index = index_data.get('base_index')
    if base_index:
        constituents.update(get_index_constituents(base_index))

    constituents.update(index_data.get('additional_constituents', []))
    result = sorted(list(constituents))
    _set_cached(cache_key, result)
    return result


def get_universe_symbols_with_keys(index_name: str) -> List[Tuple[str, str]]:
    """
    Get (symbol, instrument_key) pairs for a given index.
    Used by scanners that need both.
    Falls back to symbols-only with empty keys if DB unavailable.
    """
    cache_key = f"keys:{index_name}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    if _DB_AVAILABLE:
        try:
            with sync_engine.connect() as conn:
                if index_name.upper() in ("ALL", "ALL STOCKS"):
                    result = conn.execute(text(
                        "SELECT symbol, instrument_key FROM instrument_master "
                        "WHERE is_active = TRUE AND instrument_key IS NOT NULL "
                        "ORDER BY symbol"
                    ))
                else:
                    result = conn.execute(text("""
                        SELECT inst.symbol, inst.instrument_key
                        FROM index_master im
                        JOIN index_constituent ic ON ic.index_id = im.index_id
                        JOIN instrument_master inst ON ic.instrument_id = inst.instrument_id
                        WHERE im.index_name = :name
                          AND ic.removed_at IS NULL
                          AND inst.is_active = TRUE
                          AND inst.instrument_key IS NOT NULL
                        ORDER BY inst.symbol
                    """), {"name": index_name})
                pairs = [(r[0], r[1]) for r in result if r[0] and r[1]]
                if pairs:
                    _set_cached(cache_key, pairs)
                    return pairs
        except Exception as e:
            logger.warning(f"get_universe_symbols_with_keys DB lookup failed for '{index_name}': {e}")

    # Fallback: symbols only, no keys
    symbols = get_index_constituents(index_name)
    return [(s, "") for s in symbols]


def get_available_indices() -> List[Dict]:
    """Get list of available indices with metadata."""
    cache_key = "available_indices"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    if _DB_AVAILABLE:
        try:
            with sync_engine.connect() as conn:
                query = text("""
                    SELECT im.index_name, im.display_name, im.description, im.category,
                           COUNT(ic.instrument_id) FILTER (WHERE ic.removed_at IS NULL) AS cnt
                    FROM index_master im
                    LEFT JOIN index_constituent ic ON im.index_id = ic.index_id
                    WHERE im.is_active = TRUE
                    GROUP BY im.index_id, im.index_name, im.display_name, im.description, im.category
                    ORDER BY im.index_name
                """)
                result = conn.execute(query)
                indices = [{
                    "name": row[0],
                    "display_name": row[1] or row[0],
                    "description": row[2] or "",
                    "category": row[3] or "Broad Market",
                    "count": row[4] or 0,
                } for row in result]
                if indices:
                    _set_cached(cache_key, indices)
                    return indices
        except Exception as e:
            logger.warning(f"DB available_indices lookup failed: {e}")

    # JSON fallback
    config = load_index_config()
    indices = []
    for name, data in config.items():
        if name.startswith('_'):
            continue
        indices.append({
            "name": name,
            "display_name": name,
            "description": data.get("description", ""),
            "category": "Broad Market",
            "count": len(get_index_constituents(name)),
        })
    return indices


def get_all_symbols() -> List[str]:
    """Get all unique symbols across all active indices."""
    cache_key = "all_symbols"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    if _DB_AVAILABLE:
        try:
            with sync_engine.connect() as conn:
                query = text("""
                    SELECT DISTINCT inst.symbol
                    FROM index_constituent ic
                    JOIN instrument_master inst ON ic.instrument_id = inst.instrument_id
                    WHERE ic.removed_at IS NULL AND inst.is_active = TRUE
                    ORDER BY inst.symbol
                """)
                result = conn.execute(query)
                symbols = sorted([row[0] for row in result])
                if symbols:
                    _set_cached(cache_key, symbols)
                    return symbols
        except Exception as e:
            logger.warning(f"DB get_all_symbols failed: {e}")

    # JSON fallback
    config = load_index_config()
    all_symbols = set()
    for name in config.keys():
        if not name.startswith('_'):
            all_symbols.update(get_index_constituents(name))
    return sorted(list(all_symbols))


def reload_config() -> Dict:
    """Force reload configuration (clears all caches)."""
    clear_cache()
    return load_index_config()


