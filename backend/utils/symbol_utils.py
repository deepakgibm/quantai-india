"""
Symbol Utilities
Shared logical for fetching active symbols and company names from the database.
Eliminates the need for hardcoded symbol lists and name dictionaries in individual services.
"""

import logging
from typing import List
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import settings
from datetime import datetime

logger = logging.getLogger(__name__)

# Cache for 1 hour to avoid hitting DB constantly for static data
CACHE_TTL = 3600

class SymbolManager:
    """
    Centralized manager for symbol metadata.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SymbolManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def __init__(self):
        if self.initialized:
            return
            
        self._engine = create_engine(settings.SYNC_DATABASE_URL)
        self._Session = sessionmaker(bind=self._engine)
        self._symbol_cache = []
        self._name_cache = {}
        self._sector_cache = {} # symbol -> sector
        self._last_refresh = None
        self.initialized = True
        
    def _refresh_cache_if_needed(self):
        """Refresh cache if expired or empty."""
        now = datetime.now()
        if (self._last_refresh is None or 
            (now - self._last_refresh).total_seconds() > CACHE_TTL or 
            not self._symbol_cache):
            self.refresh_cache()
            
    def refresh_cache(self):
        """Force refresh of symbol and name cache from DB."""
        session = self._Session()
        try:
            # Query instrument_master for official list
            logger.info("Refreshing symbol cache from database...")
            
            # Try instrument_master (new schema)
            try:
                query = text("SELECT symbol, company_name, sector FROM instrument_master WHERE is_active = TRUE")
                results = session.execute(query).fetchall()
                
                if results:
                    self._symbol_cache = [r.symbol for r in results]
                    self._name_cache = {r.symbol: r.company_name or r.symbol for r in results}
                    self._sector_cache = {r.symbol: r.sector or 'Others' for r in results}
                    self._last_refresh = datetime.now()
                    logger.info(f"Loaded {len(results)} symbols from instrument_master")
                    return
            except Exception as e:
                logger.warning(f"instrument_master query failed: {e}")
                
            # Fallback to Nifty100Daily (V2 Schema compat)
            try:
                from models_ml import Nifty100Daily
                symbols = session.query(Nifty100Daily.symbol).distinct().all()
                self._symbol_cache = [s[0] for s in symbols]
                # No names in V2 table, default to symbol
                self._name_cache = {s: s for s in self._symbol_cache} 
                self._sector_cache = {}
                self._last_refresh = datetime.now()
                logger.info(f"Loaded {len(symbols)} symbols from Nifty100Daily")
            except Exception as e:
                logger.error(f"Fallback symbol fetch failed: {e}")
                self._symbol_cache = []
                self._name_cache = {}
                self._sector_cache = {}
                
        except Exception as e:
            logger.error(f"Symbol refresh failed: {e}")
        finally:
            session.close()

    def get_nifty_symbols(self) -> List[str]:
        """Get list of active trading symbols."""
        self._refresh_cache_if_needed()
        return self._symbol_cache
    
    def get_stock_name(self, symbol: str) -> str:
        """Get company name for a symbol."""
        self._refresh_cache_if_needed()
        return self._name_cache.get(symbol, symbol)
        
    def get_stock_sector(self, symbol: str) -> str:
        """Get sector for a symbol."""
        self._refresh_cache_if_needed()
        return self._sector_cache.get(symbol, 'Others')

    def get_sector_map(self) -> dict:
        """Get full symbol -> sector map."""
        self._refresh_cache_if_needed()
        return self._sector_cache.copy()

# Global Instance
_symbol_manager = SymbolManager()

def get_all_symbols() -> List[str]:
    """Public API to get all symbols."""
    return _symbol_manager.get_nifty_symbols()

def get_nifty_symbols() -> List[str]:
    """Alias for get_all_symbols used by legacy services."""
    return get_all_symbols()

def get_company_name(symbol: str) -> str:
    """Public API to get company name."""
    return _symbol_manager.get_stock_name(symbol)

def get_stock_sector(symbol: str) -> str:
    """Public API to get stock sector."""
    return _symbol_manager.get_stock_sector(symbol)
