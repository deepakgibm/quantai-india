"""
DragonflyDB/Redis Caching Layer - Production Mode
PRODUCTION MANDATE: No in-memory fallbacks. Fail-fast if cache unavailable.
"""

import json
import hashlib
import logging
from functools import wraps
from typing import Any, Optional, Callable

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.critical("FATAL: redis-py not installed. Cache layer requires DragonflyDB.")

from config import settings


class CacheUnavailableError(Exception):
    """Raised when DragonflyDB/Redis is not available."""
    pass


class CacheManager:
    """
    Production cache manager using DragonflyDB (Redis-compatible).
    PRODUCTION MANDATE: No in-memory fallbacks. Fail-fast if unavailable.
    """
    
    def __init__(self):
        self._redis_client: Optional[Any] = None
        self._is_connected: bool = False
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis/DragonflyDB connection. Fail-fast if unavailable."""
        if not REDIS_AVAILABLE:
            logger.critical("DragonflyDB client (redis-py) not available")
            self._is_connected = False
            return
        
        try:
            redis_url = getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0')
            self._redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self._redis_client.ping()
            self._is_connected = True
            logger.info(f"DragonflyDB/Redis connected: {redis_url}")
        except Exception as e:
            logger.critical(f"DragonflyDB/Redis connection failed: {e}")
            self._redis_client = None
            self._is_connected = False
    
    def _ensure_connected(self):
        """Ensure cache is connected. Raises CacheUnavailableError if not."""
        if not self._is_connected or not self._redis_client:
            raise CacheUnavailableError("DragonflyDB/Redis is not available")
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a unique cache key from function arguments."""
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        return f"quantai:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache. Returns None on cache miss, raises on connection error."""
        self._ensure_connected()
        try:
            value = self._redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except redis.ConnectionError as e:
            logger.error(f"DragonflyDB connection error: {e}")
            self._is_connected = False
            raise CacheUnavailableError(f"Cache connection lost: {e}")
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            raise
    
    def set(self, key: str, value: Any, ttl: int = 60) -> bool:
        """Set value in cache with TTL (seconds). Raises on connection error."""
        self._ensure_connected()
        try:
            self._redis_client.setex(key, ttl, json.dumps(value, default=str))
            return True
        except redis.ConnectionError as e:
            logger.error(f"DragonflyDB connection error: {e}")
            self._is_connected = False
            raise CacheUnavailableError(f"Cache connection lost: {e}")
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            raise
    
    def delete(self, key: str) -> bool:
        """Delete value from cache. Raises on connection error."""
        self._ensure_connected()
        try:
            self._redis_client.delete(key)
            return True
        except redis.ConnectionError as e:
            logger.error(f"DragonflyDB connection error: {e}")
            self._is_connected = False
            raise CacheUnavailableError(f"Cache connection lost: {e}")
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            raise
    
    def clear_pattern(self, pattern: str) -> bool:
        """Clear all keys matching pattern. Raises on connection error."""
        self._ensure_connected()
        try:
            keys = self._redis_client.keys(f"quantai:{pattern}*")
            if keys:
                self._redis_client.delete(*keys)
            return True
        except redis.ConnectionError as e:
            logger.error(f"DragonflyDB connection error: {e}")
            self._is_connected = False
            raise CacheUnavailableError(f"Cache connection lost: {e}")
        except Exception as e:
            logger.error(f"Cache clear_pattern error: {e}")
            raise
    
    def get_status(self) -> dict:
        """Get cache status info."""
        status = {
            "dragonfly_available": self._is_connected,
            "backend": "dragonfly" if self._is_connected else "unavailable",
        }
        
        if self._redis_client and self._is_connected:
            try:
                info = self._redis_client.info("memory")
                status["memory_used"] = info.get("used_memory_human", "N/A")
            except Exception:
                pass
        
        return status
    
    def is_available(self) -> bool:
        """Check if cache is available."""
        return self._is_connected


# Singleton cache manager
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get singleton cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cache_result(ttl: int = 60, prefix: str = "", fail_silently: bool = False):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time-to-live in seconds (default 60)
        prefix: Optional prefix for cache key
        fail_silently: If True, continue without cache on error. Default False (fail-fast).
    
    Usage:
        @cache_result(ttl=60)
        async def get_momentum_data():
            ...
    """
    def decorator(fn: Callable):
        @wraps(fn)
        async def async_wrapper(*args, **kwargs):
            cache = get_cache_manager()
            key_prefix = prefix or fn.__name__
            cache_key = cache._generate_key(key_prefix, *args, **kwargs)
            
            try:
                # Try to get from cache
                cached = cache.get(cache_key)
                if cached is not None:
                    logger.debug(f"Cache HIT: {key_prefix}")
                    return cached
            except CacheUnavailableError:
                if not fail_silently:
                    raise
                logger.warning(f"Cache unavailable for {key_prefix}, executing without cache")
            
            # Execute function and cache result
            logger.debug(f"Cache MISS: {key_prefix}")
            result = await fn(*args, **kwargs)
            
            try:
                cache.set(cache_key, result, ttl)
            except CacheUnavailableError:
                if not fail_silently:
                    raise
                logger.warning(f"Failed to cache result for {key_prefix}")
            
            return result
        
        @wraps(fn)
        def sync_wrapper(*args, **kwargs):
            cache = get_cache_manager()
            key_prefix = prefix or fn.__name__
            cache_key = cache._generate_key(key_prefix, *args, **kwargs)
            
            try:
                # Try to get from cache
                cached = cache.get(cache_key)
                if cached is not None:
                    logger.debug(f"Cache HIT: {key_prefix}")
                    return cached
            except CacheUnavailableError:
                if not fail_silently:
                    raise
                logger.warning(f"Cache unavailable for {key_prefix}, executing without cache")
            
            # Execute function and cache result
            logger.debug(f"Cache MISS: {key_prefix}")
            result = fn(*args, **kwargs)
            
            try:
                cache.set(cache_key, result, ttl)
            except CacheUnavailableError:
                if not fail_silently:
                    raise
                logger.warning(f"Failed to cache result for {key_prefix}")
            
            return result
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(fn):
            return async_wrapper
        return sync_wrapper
    
    return decorator
