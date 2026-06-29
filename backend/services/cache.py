"""
DragonflyDB/Redis Caching Layer - Wrapper delegating to dragonfly_client.py
PRODUCTION MANDATE: No in-memory fallbacks. Fail-fast if cache unavailable.
"""

from typing import Any, Optional, Callable
from services.dragonfly_client import get_cache

class CacheManager:
    """
    Cache manager delegating to the unified high-performance CacheManager in dragonfly_client.
    """
    
    def __init__(self):
        self._client = get_cache()
    
    def get(self, key: str) -> Optional[Any]:
        return self._client.get(key)
        
    def set(self, key: str, value: Any, ttl: int = 60) -> bool:
        return self._client.set(key, value, ttl)
        
    def delete(self, key: str) -> bool:
        return self._client.delete(key)
        
    def clear_pattern(self, pattern: str) -> bool:
        return self._client.clear_pattern(pattern)
        
    def get_status(self) -> dict:
        stats = self._client.get_stats()
        return {
            "dragonfly_available": stats.get("is_connected_sync", False),
            "backend": "dragonfly" if stats.get("is_connected_sync", False) else "unavailable",
        }
        
    def is_available(self) -> bool:
        return self._client.is_available()


# Singleton cache manager
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get singleton cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
