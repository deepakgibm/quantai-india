"""
Index Constituents Configuration Loader
========================================
Updated to prioritize database-driven lookup with JSON fallback.
Supports hierarchical index definitions (e.g., NIFTY 100 includes NIFTY 50).
"""

import json
import os
from typing import Dict, List
from functools import lru_cache
import logging
from sqlalchemy import text

# Try to import DB components
try:
    from database import sync_engine
    _DB_AVAILABLE = True
except ImportError:
    _DB_AVAILABLE = False

logger = logging.getLogger(__name__)

# Path to the config file
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'index_constituents.json')


@lru_cache(maxsize=1)
def load_index_config() -> Dict:
    """Load index constituents configuration from JSON file."""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load index config JSON: {e}")
    return {}


def get_index_constituents(index_name: str) -> List[str]:
    """
    Get constituent symbols for an index.
    Prioritizes Database, falls back to JSON.
    """
    if _DB_AVAILABLE:
        try:
            with sync_engine.connect() as conn:
                # Recursive query for hierarchical indices
                query = text("""
                    WITH RECURSIVE index_tree AS (
                        SELECT index_id, base_index_id FROM index_master WHERE index_name = :name
                        UNION ALL
                        SELECT im.index_id, im.base_index_id 
                        FROM index_master im
                        JOIN index_tree it ON im.index_id = it.base_index_id
                    )
                    SELECT DISTINCT inst.symbol 
                    FROM index_constituent ic
                    JOIN instrument_master inst ON ic.instrument_id = inst.instrument_id
                    WHERE ic.index_id IN (SELECT index_id FROM index_tree)
                    AND inst.is_active = True
                """)
                result = conn.execute(query, {"name": index_name})
                symbols = [row[0] for row in result]
                if symbols:
                    logger.info(f"Loaded {len(symbols)} symbols for {index_name} from DB")
                    return sorted(symbols)
        except Exception as e:
            logger.warning(f"Database index lookup failed for {index_name}: {e}. Falling back to JSON.")

    # Fallback to JSON
    config = load_index_config()
    if index_name not in config:
        return []
    
    index_data = config[index_name]
    constituents = set(index_data.get('constituents', []))
    
    base_index = index_data.get('base_index')
    if base_index:
        constituents.update(get_index_constituents(base_index))
    
    constituents.update(index_data.get('additional_constituents', []))
    return sorted(list(constituents))


def get_available_indices() -> List[Dict]:
    """Get list of available indices with metadata."""
    if _DB_AVAILABLE:
        try:
            with sync_engine.connect() as conn:
                query = text("""
                    SELECT im.index_name, im.description, COUNT(ic.instrument_id) 
                    FROM index_master im
                    LEFT JOIN index_constituent ic ON im.index_id = ic.index_id
                    WHERE im.is_active = True
                    GROUP BY im.index_id, im.index_name, im.description
                """)
                result = conn.execute(query)
                return [{
                    "name": row[0],
                    "description": row[1] or "",
                    "count": row[2]
                } for row in result]
        except Exception as e:
            logger.warning(f"Database available indices lookup failed: {e}")

    # Fallback to JSON
    config = load_index_config()
    indices = []
    for name, data in config.items():
        if name.startswith('_'): continue
        indices.append({
            "name": name,
            "description": data.get("description", ""),
            "count": len(get_index_constituents(name))
        })
    return indices


def get_all_symbols() -> List[str]:
    """Get all unique symbols across active indices."""
    if _DB_AVAILABLE:
        try:
            with sync_engine.connect() as conn:
                query = text("""
                    SELECT DISTINCT inst.symbol 
                    FROM index_constituent ic
                    JOIN instrument_master inst ON ic.instrument_id = inst.instrument_id
                    WHERE inst.is_active = True
                """)
                result = conn.execute(query)
                return sorted([row[0] for row in result])
        except Exception as e:
            logger.warning(f"Database get_all_symbols failed: {e}")

    # Fallback to JSON
    config = load_index_config()
    all_symbols = set()
    for name in config.keys():
        if not name.startswith('_'):
            all_symbols.update(get_index_constituents(name))
    return sorted(list(all_symbols))


def clear_cache():
    """Clear the configuration cache."""
    load_index_config.cache_clear()


def reload_config() -> Dict:
    """Reload configuration."""
    clear_cache()
    return load_index_config()
