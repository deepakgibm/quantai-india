import json
import logging
from typing import Optional, Dict, Any
from services.cache import get_cache_manager
from services.price_manager.market_status_service import get_market_status_service, MarketStatus

logger = logging.getLogger(__name__)

class PriceCache:
    """
    Standardizes caching keys, TTL policies, and retrieval logic for stock prices.
    Uses Dragonfly/Redis as the primary caching provider.
    """
    
    def __init__(self):
        self._cache = get_cache_manager()
        self._status_service = get_market_status_service()
        self._local_cache: Dict[str, Dict[str, Any]] = {}  # Thread-safe in-memory cache

    def _get_keys(self, symbol: str) -> list:
        symbol_upper = symbol.upper()
        return [
            f"price:{symbol_upper}",
            f"qai:tick:{symbol_upper}"
        ]

    def get(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached price from Redis or local memory fallback."""
        symbol_upper = symbol.upper()
        keys = self._get_keys(symbol_upper)
        
        # 1. Attempt Redis retrieval
        if self._cache.is_available():
            try:
                for k in keys:
                    val = self._cache.get(k)
                    if val:
                        if isinstance(val, str):
                            try:
                                val = json.loads(val)
                            except ValueError:
                                pass
                        if isinstance(val, dict):
                            # Populate back into local cache
                            self._local_cache[symbol_upper] = val
                            return val
            except Exception as e:
                logger.warning(f"Cache: Redis error retrieving {symbol_upper}: {e}")

        # 2. Local memory fallback
        return self._local_cache.get(symbol_upper)

    def set(self, symbol: str, price_data: Dict[str, Any]) -> bool:
        """Set cached price in Redis and local memory."""
        symbol_upper = symbol.upper()
        keys = self._get_keys(symbol_upper)
        
        # Save to local cache first
        self._local_cache[symbol_upper] = price_data
        
        # Determine TTL based on Market Hours
        status = self._status_service.get_status()
        if status == MarketStatus.OPEN:
            ttl = 10  # short TTL during live market
        elif status in (MarketStatus.HOLIDAY, MarketStatus.WEEKEND, MarketStatus.CLOSED):
            ttl = 18000  # 5 hours for EOD/closed prices
        else:
            ttl = 300  # 5 minutes default
            
        success = True
        if self._cache.is_available():
            try:
                for k in keys:
                    self._cache.set(k, price_data, ttl=ttl)
            except Exception as e:
                logger.warning(f"Cache: Redis error setting {symbol_upper}: {e}")
                success = False
                
        return success

    def clear(self, symbol: str):
        symbol_upper = symbol.upper()
        keys = self._get_keys(symbol_upper)
        if symbol_upper in self._local_cache:
            del self._local_cache[symbol_upper]
        if self._cache.is_available():
            for k in keys:
                self._cache.delete(k)

_price_cache = None

def get_price_cache() -> PriceCache:
    global _price_cache
    if _price_cache is None:
        _price_cache = PriceCache()
    return _price_cache
