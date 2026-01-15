"""
Backward-Compatibility Wrapper - DEPRECATED

This module is deprecated. Please use dragonfly_client instead:

    from services.dragonfly_client import get_cache, CacheKeys, ...

This wrapper re-exports all symbols from dragonfly_client for backward compatibility.
"""

# Re-export everything from dragonfly_client for backward compatibility
from services.dragonfly_client import (
    # Configuration
    DRAGONFLY_HOST,
    DRAGONFLY_PORT,
    DRAGONFLY_DB,
    
    # TTL Policies
    TTLPolicy,
    
    # Exceptions
    CacheUnavailableError,
    
    # Cache Keys
    CacheKeys,
    
    # Cache Manager
    CacheManager,
    
    # Singleton Accessor
    get_cache,
    
    # Convenience Functions
    cache_get,
    cache_set,
    cache_delete,
    cache_stats,
)

# Logging deprecation warning on import
import warnings
warnings.warn(
    "memcached_client is deprecated. Use dragonfly_client instead.",
    DeprecationWarning,
    stacklevel=2
)
