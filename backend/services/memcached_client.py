"""
Backward-Compatibility Wrapper - DEPRECATED

This module is deprecated. Please use dragonfly_client instead:

    from services.dragonfly_client import get_cache, CacheKeys, ...

This wrapper re-exports all symbols from dragonfly_client for backward compatibility.
"""

# Re-export everything from dragonfly_client for backward compatibility

# Logging deprecation warning on import
import warnings
warnings.warn(
    "memcached_client is deprecated. Use dragonfly_client instead.",
    DeprecationWarning,
    stacklevel=2
)
