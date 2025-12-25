"""
Redis Caching Layer
Provides caching decorators for API endpoints and computed results.
"""

import json
import hashlib
import logging
from functools import wraps
from typing import Any, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import redis, fall back to in-memory cache if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory cache fallback")

from config import settings


class CacheManager:
    """
    Unified cache manager with Redis primary and in-memory fallback.
    """
    
    def __init__(self):
        self._memory_cache: dict = {}
        self._memory_expiry: dict = {}
        self._redis_client: Optional[Any] = None
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis connection if available."""
        if not REDIS_AVAILABLE:
            return
        
        try:
            # Use Celery broker URL which is already configured for Redis
            redis_url = getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0')
            self._redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self._redis_client.ping()
            logger.info(f"Redis cache connected: {redis_url}")
        except Exception as e:
            logger.warning(f"Redis connection failed, using memory cache: {e}")
            self._redis_client = None
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a unique cache key from function arguments."""
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        return f"quantai:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        # Try Redis first
        if self._redis_client:
            try:
                value = self._redis_client.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
        
        # Fall back to memory cache
        if key in self._memory_cache:
            expiry = self._memory_expiry.get(key)
            if expiry and datetime.now().timestamp() < expiry:
                return self._memory_cache[key]
            else:
                # Expired, remove from cache
                self._memory_cache.pop(key, None)
                self._memory_expiry.pop(key, None)
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = 60):
        """Set value in cache with TTL (seconds)."""
        # Try Redis first
        if self._redis_client:
            try:
                self._redis_client.setex(key, ttl, json.dumps(value, default=str))
                return
            except Exception as e:
                logger.warning(f"Redis set error: {e}")
        
        # Fall back to memory cache
        self._memory_cache[key] = value
        self._memory_expiry[key] = datetime.now().timestamp() + ttl
    
    def delete(self, key: str):
        """Delete value from cache."""
        if self._redis_client:
            try:
                self._redis_client.delete(key)
            except Exception:
                pass
        
        self._memory_cache.pop(key, None)
        self._memory_expiry.pop(key, None)
    
    def clear_pattern(self, pattern: str):
        """Clear all keys matching pattern."""
        if self._redis_client:
            try:
                keys = self._redis_client.keys(f"quantai:{pattern}*")
                if keys:
                    self._redis_client.delete(*keys)
            except Exception:
                pass
        
        # Clear memory cache keys matching pattern
        to_delete = [k for k in self._memory_cache if pattern in k]
        for k in to_delete:
            self._memory_cache.pop(k, None)
            self._memory_expiry.pop(k, None)
    
    def get_status(self) -> dict:
        """Get cache status info."""
        status = {
            "redis_available": self._redis_client is not None,
            "memory_cache_size": len(self._memory_cache),
        }
        
        if self._redis_client:
            try:
                info = self._redis_client.info("memory")
                status["redis_memory_used"] = info.get("used_memory_human", "N/A")
            except Exception:
                pass
        
        return status


# Singleton cache manager
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get singleton cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cache_result(ttl: int = 60, prefix: str = ""):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time-to-live in seconds (default 60)
        prefix: Optional prefix for cache key
    
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
            
            # Try to get from cache
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache HIT: {key_prefix}")
                return cached
            
            # Execute function and cache result
            logger.debug(f"Cache MISS: {key_prefix}")
            result = await fn(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        @wraps(fn)
        def sync_wrapper(*args, **kwargs):
            cache = get_cache_manager()
            key_prefix = prefix or fn.__name__
            cache_key = cache._generate_key(key_prefix, *args, **kwargs)
            
            # Try to get from cache
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache HIT: {key_prefix}")
                return cached
            
            # Execute function and cache result
            logger.debug(f"Cache MISS: {key_prefix}")
            result = fn(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(fn):
            return async_wrapper
        return sync_wrapper
    
    return decorator
