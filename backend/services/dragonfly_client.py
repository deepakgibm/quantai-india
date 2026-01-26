"""
Dragonfly/Redis Cache Client - High-Performance Cache Layer (PRODUCTION MODE)
PRODUCTION MANDATE: No in-memory fallbacks. Fail-fast if cache unavailable.

Dragonfly is Redis-compatible but 25x faster with 4x memory efficiency.
"""

import json
import logging
from typing import Optional, Any, Dict, List
import os

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================
DRAGONFLY_HOST = os.getenv("DRAGONFLY_HOST", "localhost")
DRAGONFLY_PORT = int(os.getenv("DRAGONFLY_PORT", "6379"))
DRAGONFLY_DB = int(os.getenv("DRAGONFLY_DB", "0"))


# =============================================================================
# TTL Policies (in seconds)
# =============================================================================
class TTLPolicy:
    """TTL policies for different data types."""
    CANDLE = 60          # Latest candle - 1 minute
    INDICATOR = 5        # Computed indicators - 5 seconds (refresh frequently)
    SCANNER = 5          # Scanner results - 5 seconds
    SNAPSHOT = 5         # Symbol snapshots - 5 seconds
    WARMUP = 300         # Warm-up status - 5 minutes
    STRATEGY = 10        # Strategy signals - 10 seconds
    METADATA = 3600      # Static metadata - 1 hour
    
    # NIFTY 100 Top Movers
    TOP_MOVERS_LIVE = 10     # During market hours: 10 seconds
    TOP_MOVERS_EOD = 18000   # After market: 5 hours (until next session)


# =============================================================================
# Custom Exceptions
# =============================================================================
class CacheUnavailableError(Exception):
    """Raised when DragonflyDB/Redis is not available."""
    pass


# =============================================================================
# Cache Key Builder
# =============================================================================
class CacheKeys:
    """
    Standardized cache key generation.
    All keys are prefixed with 'qai:' for namespace isolation.
    """
    PREFIX = "qai"
    
    @staticmethod
    def candle(symbol: str, interval: str) -> str:
        """Latest candle for symbol + interval."""
        return f"{CacheKeys.PREFIX}:candle:{symbol}:{interval}"
    
    @staticmethod
    def indicator(symbol: str, interval: str) -> str:
        """All indicators for symbol + interval."""
        return f"{CacheKeys.PREFIX}:ind:{symbol}:{interval}"
    
    @staticmethod
    def scanner(scanner_type: str) -> str:
        """Scanner results by type."""
        return f"{CacheKeys.PREFIX}:scan:{scanner_type}"
    
    @staticmethod
    def snapshot(symbol: str) -> str:
        """Symbol snapshot with all data."""
        return f"{CacheKeys.PREFIX}:snap:{symbol}"
    
    @staticmethod
    def sector_snapshot(sector: str) -> str:
        """Sector snapshot with aggregated data."""
        return f"{CacheKeys.PREFIX}:sector:{sector}"
    
    @staticmethod
    def all_snapshots() -> str:
        """All symbol snapshots combined."""
        return f"{CacheKeys.PREFIX}:snap:all"
    
    @staticmethod
    def heatmap_all() -> str:
        """Full heatmap data (all sectors)."""
        return f"{CacheKeys.PREFIX}:heatmap:all"

    @staticmethod
    def momentum() -> str:
        """Momentum scanner results."""
        return f"{CacheKeys.PREFIX}:scan:momentum"
    
    @staticmethod
    def breakout() -> str:
        """Breakout scanner results."""
        return f"{CacheKeys.PREFIX}:scan:breakout"
    
    @staticmethod
    def reversal() -> str:
        """Reversal scanner results."""
        return f"{CacheKeys.PREFIX}:scan:reversal"
    
    @staticmethod
    def signals() -> str:
        """Active strategy signals."""
        return f"{CacheKeys.PREFIX}:signals:active"
    
    @staticmethod
    def warmup_status() -> str:
        """Cache warm-up status."""
        return f"{CacheKeys.PREFIX}:warmup:status"
    
    @staticmethod
    def metrics() -> str:
        """Cache metrics (hits, misses)."""
        return f"{CacheKeys.PREFIX}:metrics"
    
    @staticmethod
    def nifty100_top_movers(trading_date: str) -> str:
        """NIFTY 100 Top Gainers/Losers by trading date."""
        return f"nifty100:top_gainers_losers:{trading_date}"
    
    @staticmethod
    def worker_status() -> str:
        """Worker process status."""
        return f"{CacheKeys.PREFIX}:worker:status"


# =============================================================================
# Cache Manager (Dragonfly/Redis) - PRODUCTION MODE
# =============================================================================
class CacheManager:
    """
    High-performance cache manager using Dragonfly (Redis-compatible).
    PRODUCTION MANDATE: No in-memory fallbacks. Fail-fast if unavailable.
    
    Features:
    - Connection pooling
    - Automatic JSON serialization
    - TTL management
    - Hit/miss tracking
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._client: Optional[redis.Redis] = None
        self._hits = 0
        self._misses = 0
        self._is_connected = False
        
        # Try to connect to Dragonfly/Redis
        self._connect()
        self._initialized = True
    
    def _connect(self):
        """Connect to Dragonfly/Redis server. Log critical error if unavailable."""
        if not REDIS_AVAILABLE:
            logger.critical("FATAL: redis-py not installed. DragonflyDB cache layer unavailable.")
            self._is_connected = False
            return
        
        try:
            # Create connection pool
            pool = redis.ConnectionPool(
                host=DRAGONFLY_HOST,
                port=DRAGONFLY_PORT,
                db=DRAGONFLY_DB,
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0,
                max_connections=20,
            )
            
            self._client = redis.Redis(connection_pool=pool)
            
            # Test connection
            self._client.ping()
            self._is_connected = True
            logger.info(f"Connected to Dragonfly/Redis at {DRAGONFLY_HOST}:{DRAGONFLY_PORT}")
                
        except Exception as e:
            logger.critical(f"DragonflyDB/Redis connection failed: {e}")
            self._client = None
            self._is_connected = False
    
    def _ensure_connected(self):
        """Ensure cache is connected. Raises CacheUnavailableError if not."""
        if not self._is_connected or not self._client:
            raise CacheUnavailableError("DragonflyDB/Redis is not available")
    
    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        return json.dumps(value)
    
    def _deserialize(self, value: str) -> Any:
        """Deserialize JSON string to value."""
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache. Raises CacheUnavailableError if not connected."""
        self._ensure_connected()
        import time
        start = time.perf_counter()
        try:
            value = self._client.get(key)
            duration = time.perf_counter() - start
            
            # Record metrics
            try:
                from core.observability.metrics import get_metrics
                metrics = get_metrics()
                if value is not None:
                    self._hits += 1
                    metrics.record_cache_operation("get", "hit", duration)
                else:
                    self._misses += 1
                    metrics.record_cache_operation("get", "miss", duration)
            except ImportError:
                if value is not None:
                    self._hits += 1
                else:
                    self._misses += 1
                    
            return self._deserialize(value)
        except redis.ConnectionError as e:
            logger.error(f"DragonflyDB connection error: {e}")
            self._is_connected = False
            raise CacheUnavailableError(f"Cache connection lost: {e}")
        except Exception as e:
            duration = time.perf_counter() - start
            logger.error(f"Cache get error: {e}")
            # Record error metric
            try:
                from core.observability.metrics import get_metrics
                get_metrics().record_cache_operation("get", "error", duration)
            except ImportError:
                pass
            self._misses += 1
            raise
    
    def set(self, key: str, value: Any, ttl: int = TTLPolicy.INDICATOR) -> bool:
        """Set value in cache with TTL. Raises CacheUnavailableError if not connected."""
        self._ensure_connected()
        import time
        start = time.perf_counter()
        try:
            self._client.setex(key, ttl, self._serialize(value))
            duration = time.perf_counter() - start
            
            # Record metrics
            try:
                from core.observability.metrics import get_metrics
                get_metrics().record_cache_operation("set", "success", duration)
            except ImportError:
                pass
                
            return True
        except redis.ConnectionError as e:
            logger.error(f"DragonflyDB connection error: {e}")
            self._is_connected = False
            raise CacheUnavailableError(f"Cache connection lost: {e}")
        except Exception as e:
            duration = time.perf_counter() - start
            logger.error(f"Cache set error: {e}")
            # Record error metric
            try:
                from core.observability.metrics import get_metrics
                get_metrics().record_cache_operation("set", "error", duration)
            except ImportError:
                pass
            raise
    
    def delete(self, key: str) -> bool:
        """Delete key from cache. Raises CacheUnavailableError if not connected."""
        self._ensure_connected()
        try:
            self._client.delete(key)
            return True
        except redis.ConnectionError as e:
            logger.error(f"DragonflyDB connection error: {e}")
            self._is_connected = False
            raise CacheUnavailableError(f"Cache connection lost: {e}")
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            raise
    
    def get_multi(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache. Raises CacheUnavailableError if not connected."""
        self._ensure_connected()
        try:
            values = self._client.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    result[key] = self._deserialize(value)
                    self._hits += 1
                else:
                    self._misses += 1
            return result
        except redis.ConnectionError as e:
            logger.error(f"DragonflyDB connection error: {e}")
            self._is_connected = False
            raise CacheUnavailableError(f"Cache connection lost: {e}")
        except Exception as e:
            logger.error(f"Cache get_multi error: {e}")
            raise
    
    def set_multi(self, items: Dict[str, Any], ttl: int = TTLPolicy.INDICATOR) -> bool:
        """Set multiple values in cache. Raises CacheUnavailableError if not connected."""
        self._ensure_connected()
        try:
            pipe = self._client.pipeline()
            for key, value in items.items():
                pipe.setex(key, ttl, self._serialize(value))
            pipe.execute()
            return True
        except redis.ConnectionError as e:
            logger.error(f"DragonflyDB connection error: {e}")
            self._is_connected = False
            raise CacheUnavailableError(f"Cache connection lost: {e}")
        except Exception as e:
            logger.error(f"Cache set_multi error: {e}")
            raise
    
    # ==========================================================================
    # Redis-specific features (sorted sets for rankings)
    # ==========================================================================
    
    def zadd_momentum(self, symbol: str, change_pct: float) -> bool:
        """Add symbol to momentum sorted set. Raises CacheUnavailableError if not connected."""
        self._ensure_connected()
        try:
            self._client.zadd(f"{CacheKeys.PREFIX}:zset:momentum", {symbol: change_pct})
            return True
        except redis.ConnectionError as e:
            logger.error(f"DragonflyDB connection error: {e}")
            self._is_connected = False
            raise CacheUnavailableError(f"Cache connection lost: {e}")
        except Exception as e:
            logger.error(f"ZADD error: {e}")
            raise
    
    def get_top_gainers(self, limit: int = 20) -> List[tuple]:
        """Get top gainers from sorted set. Raises CacheUnavailableError if not connected."""
        self._ensure_connected()
        try:
            return self._client.zrevrange(
                f"{CacheKeys.PREFIX}:zset:momentum", 
                0, limit - 1, 
                withscores=True
            )
        except redis.ConnectionError as e:
            logger.error(f"DragonflyDB connection error: {e}")
            self._is_connected = False
            raise CacheUnavailableError(f"Cache connection lost: {e}")
        except Exception as e:
            logger.error(f"ZREVRANGE error: {e}")
            raise
    
    def get_top_losers(self, limit: int = 20) -> List[tuple]:
        """Get top losers from sorted set. Raises CacheUnavailableError if not connected."""
        self._ensure_connected()
        try:
            return self._client.zrange(
                f"{CacheKeys.PREFIX}:zset:momentum", 
                0, limit - 1, 
                withscores=True
            )
        except redis.ConnectionError as e:
            logger.error(f"DragonflyDB connection error: {e}")
            self._is_connected = False
            raise CacheUnavailableError(f"Cache connection lost: {e}")
        except Exception as e:
            logger.error(f"ZRANGE error: {e}")
            raise
    
    def publish(self, channel: str, message: Any) -> bool:
        """Publish message to channel. Raises CacheUnavailableError if not connected."""
        self._ensure_connected()
        try:
            self._client.publish(channel, self._serialize(message))
            return True
        except redis.ConnectionError as e:
            logger.error(f"DragonflyDB connection error: {e}")
            self._is_connected = False
            raise CacheUnavailableError(f"Cache connection lost: {e}")
        except Exception as e:
            logger.error(f"PUBLISH error: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        return {
            "backend": "dragonfly" if self._is_connected else "unavailable",
            "is_connected": self._is_connected,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
        }
    
    def reset_stats(self):
        """Reset hit/miss counters."""
        self._hits = 0
        self._misses = 0
    
    def flush(self):
        """Flush all cache data. Raises CacheUnavailableError if not connected."""
        self._ensure_connected()
        try:
            # Only flush our namespace
            keys = self._client.keys(f"{CacheKeys.PREFIX}:*")
            if keys:
                self._client.delete(*keys)
        except redis.ConnectionError as e:
            logger.error(f"DragonflyDB connection error: {e}")
            self._is_connected = False
            raise CacheUnavailableError(f"Cache connection lost: {e}")
        except Exception as e:
            logger.error(f"Cache flush error: {e}")
            raise
    
    def info(self) -> Dict[str, Any]:
        """Get Dragonfly/Redis server info. Raises CacheUnavailableError if not connected."""
        self._ensure_connected()
        try:
            info = self._client.info()
            return {
                "server": info.get("redis_version", "unknown"),
                "used_memory_human": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
            }
        except redis.ConnectionError as e:
            logger.error(f"DragonflyDB connection error: {e}")
            self._is_connected = False
            raise CacheUnavailableError(f"Cache connection lost: {e}")
        except Exception as e:
            logger.error(f"Cache info error: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if cache is available."""
        return self._is_connected


# =============================================================================
# Singleton Accessor
# =============================================================================
_cache_manager: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


# =============================================================================
# Convenience Functions
# =============================================================================
def cache_get(key: str) -> Optional[Any]:
    """Get value from cache. Raises CacheUnavailableError if not connected."""
    return get_cache().get(key)


def cache_set(key: str, value: Any, ttl: int = TTLPolicy.INDICATOR) -> bool:
    """Set value in cache. Raises CacheUnavailableError if not connected."""
    return get_cache().set(key, value, ttl)


def cache_delete(key: str) -> bool:
    """Delete key from cache. Raises CacheUnavailableError if not connected."""
    return get_cache().delete(key)


def cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    return get_cache().get_stats()
