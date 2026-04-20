"""
Dragonfly/Redis Cache Client - High-Performance Cache Layer (PRODUCTION MODE)
PRODUCTION MANDATE: No in-memory fallbacks. Fail-fast if cache unavailable.

Dragonfly is Redis-compatible but 25x faster with 4x memory efficiency.
Supports both Sync and Async modes for high-performance FastAPI and Background Workers.
"""

import json
import logging
from typing import Optional, Any, Dict, List, Callable
import os

logger = logging.getLogger(__name__)

# =============================================================================
# Redis Import Handling (Sync and Async)
# =============================================================================
try:
    import redis as redis_sync
    REDIS_SYNC_AVAILABLE = True
except ImportError:
    redis_sync = None
    REDIS_SYNC_AVAILABLE = False

try:
    import redis.asyncio as redis_async
    REDIS_ASYNC_AVAILABLE = True
except (ImportError, AttributeError):
    redis_async = None
    REDIS_ASYNC_AVAILABLE = False

# =============================================================================
# Configuration
# =============================================================================
# Dragonfly/Redis Configuration
DRAGONFLY_HOST = os.getenv("DRAGONFLY_HOST", "localhost")
DRAGONFLY_PORT = int(os.getenv("DRAGONFLY_PORT", "6379"))
DRAGONFLY_DB = int(os.getenv("DRAGONFLY_DB", "0"))
DRAGONFLY_USE_CLUSTER = os.getenv("DRAGONFLY_USE_CLUSTER", "false").lower() == "true"

# DEV_MODE: Enable in-memory fallback when Redis/Dragonfly is unavailable
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

# In-memory cache for DEV_MODE fallback
_in_memory_cache: Dict[str, Any] = {}

class TTLPolicy:
    """TTL policies for different data types."""
    CANDLE = 60
    INDICATOR = 5
    SCANNER = 5
    SNAPSHOT = 5
    WARMUP = 300
    STRATEGY = 10
    METADATA = 3600
    TOP_MOVERS_LIVE = 10
    TOP_MOVERS_EOD = 18000


class CacheUnavailableError(Exception):
    """Raised when DragonflyDB/Redis is not available."""
    pass


class CacheKeys:
    """Standardized cache key generation."""
    PREFIX = "qai"
    
    @staticmethod
    def candle(symbol: str, interval: str) -> str: return f"{CacheKeys.PREFIX}:candle:{symbol}:{interval}"
    @staticmethod
    def indicator(symbol: str, interval: str) -> str: return f"{CacheKeys.PREFIX}:ind:{symbol}:{interval}"
    @staticmethod
    def scanner(scanner_type: str) -> str: return f"{CacheKeys.PREFIX}:scan:{scanner_type}"
    @staticmethod
    def snapshot(symbol: str) -> str: return f"{CacheKeys.PREFIX}:snap:{symbol}"
    @staticmethod
    def sector_snapshot(sector: str) -> str: return f"{CacheKeys.PREFIX}:sector:{sector}"
    @staticmethod
    def all_snapshots() -> str: return f"{CacheKeys.PREFIX}:snap:all"
    @staticmethod
    def heatmap_all() -> str: return f"{CacheKeys.PREFIX}:heatmap:all"
    @staticmethod
    def momentum() -> str: return f"{CacheKeys.PREFIX}:scan:momentum"
    @staticmethod
    def breakout() -> str: return f"{CacheKeys.PREFIX}:scan:breakout"
    @staticmethod
    def reversal() -> str: return f"{CacheKeys.PREFIX}:scan:reversal"
    @staticmethod
    def signals() -> str: return f"{CacheKeys.PREFIX}:signals:active"
    @staticmethod
    def warmup_status() -> str: return f"{CacheKeys.PREFIX}:warmup:status"
    @staticmethod
    def metrics() -> str: return f"{CacheKeys.PREFIX}:metrics"
    @staticmethod
    def nifty100_top_movers(trading_date: str) -> str: return f"nifty100:top_gainers_losers:{trading_date}"
    @staticmethod
    def worker_status() -> str: return f"{CacheKeys.PREFIX}:worker:status"


class CacheManager:
    """
    High-performance cache manager supporting both Sync and Async Redis clients.
    Falls back to sync-only mode if redis.asyncio is unavailable.
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
        
        self._async_client = None
        self._sync_client = None
        self._sync_pool = None
        
        self._hits = 0
        self._misses = 0
        self._is_connected_sync = False
        self._is_connected_async = False
        
        self._initialized = True
        logger.info(f"CacheManager: Initialized (Sync={REDIS_SYNC_AVAILABLE}, Async={REDIS_ASYNC_AVAILABLE})")

    # --- SYNC METHODS (For Threads/ETL and Fallback) ---

    def _ensure_sync_connected(self):
        if not REDIS_SYNC_AVAILABLE:
            if DEV_MODE:
                logger.warning("DEV_MODE: Using in-memory cache fallback (redis-py not installed)")
                return  # Allow fallback
            raise CacheUnavailableError("redis-py not installed")
            
        if self._is_connected_sync and self._sync_client:
            return
            
        try:
            if DRAGONFLY_USE_CLUSTER:
                # Clustered configuration (Phase 3)
                startup_nodes = [{"host": DRAGONFLY_HOST, "port": DRAGONFLY_PORT}]
                self._sync_client = redis_sync.cluster.RedisCluster(
                    startup_nodes=startup_nodes,
                    decode_responses=True,
                    skip_full_coverage_check=True
                )
            else:
                if not self._sync_pool:
                    self._sync_pool = redis_sync.ConnectionPool(
                        host=DRAGONFLY_HOST, port=DRAGONFLY_PORT, db=DRAGONFLY_DB,
                        decode_responses=True, socket_timeout=0.5, max_connections=20
                    )
                self._sync_client = redis_sync.Redis(connection_pool=self._sync_pool)
            self._sync_client.ping()
            self._is_connected_sync = True
            logger.info(f"Connected to Redis/Dragonfly (Sync-{'Cluster' if DRAGONFLY_USE_CLUSTER else 'Single'}) at {DRAGONFLY_HOST}:{DRAGONFLY_PORT}")
        except Exception as e:
            logger.error(f"Sync Cache connection failed: {e}")
            self._is_connected_sync = False
            if DEV_MODE:
                logger.warning("DEV_MODE: Using in-memory cache fallback")
                return  # Allow fallback
            raise CacheUnavailableError(str(e))

    def get(self, key: str) -> Optional[Any]:
        """Synchronous cache get."""
        self._ensure_sync_connected()
        # DEV_MODE: Use in-memory fallback if Redis not connected
        if DEV_MODE and not self._is_connected_sync:
            val = _in_memory_cache.get(key)
            if val is not None:
                self._hits += 1
                return val
            self._misses += 1
            return None
        try:
            val = self._sync_client.get(key)
            if val is not None:
                self._hits += 1
                return self._deserialize(val)
            self._misses += 1
            return None
        except Exception as e:
            logger.error(f"Sync cache get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = TTLPolicy.INDICATOR) -> bool:
        """Synchronous cache set."""
        self._ensure_sync_connected()
        # DEV_MODE: Use in-memory fallback if Redis not connected
        if DEV_MODE and not self._is_connected_sync:
            _in_memory_cache[key] = value
            return True
        try:
            self._sync_client.setex(key, ttl, self._serialize(value))
            return True
        except Exception as e:
            logger.error(f"Sync cache set error: {e}")
            return False

    def mset(self, mapping: Dict[str, Any], ttl: int = TTLPolicy.INDICATOR) -> bool:
        """Synchronous pipelined batch set with TTL."""
        self._ensure_sync_connected()
        try:
            pipe = self._sync_client.pipeline()
            for key, value in mapping.items():
                pipe.setex(key, ttl, self._serialize(value))
            pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Sync mset error: {e}")
            return False

    # --- ASYNC METHODS (For FastAPI) ---

    async def _ensure_async_connected(self):
        if not REDIS_ASYNC_AVAILABLE:
            # Fall back to sync client wrapped in thread executor
            self._ensure_sync_connected()
            return
            
        if self._is_connected_async and self._async_client:
            return
            
        try:
            if DRAGONFLY_USE_CLUSTER:
                startup_nodes = [{"host": DRAGONFLY_HOST, "port": DRAGONFLY_PORT}]
                self._async_client = redis_async.cluster.RedisCluster(
                    startup_nodes=startup_nodes,
                    decode_responses=True,
                    skip_full_coverage_check=True
                )
            else:
                self._async_client = redis_async.Redis(
                    host=DRAGONFLY_HOST, port=DRAGONFLY_PORT, db=DRAGONFLY_DB,
                    decode_responses=True, socket_timeout=1.0
                )
            await self._async_client.ping()
            self._is_connected_async = True
            logger.info(f"Connected to Redis/Dragonfly (Async-{'Cluster' if DRAGONFLY_USE_CLUSTER else 'Single'}) at {DRAGONFLY_HOST}:{DRAGONFLY_PORT}")
        except Exception as e:
            logger.error(f"Async Cache connection failed: {e}")
            self._is_connected_async = False
            if DEV_MODE:
                logger.warning("DEV_MODE: Using in-memory cache fallback (async)")
                return  # Allow fallback
            raise CacheUnavailableError(str(e))

    async def get_async(self, key: str) -> Optional[Any]:
        """Async cache get - falls back to sync if async unavailable."""
        if not REDIS_ASYNC_AVAILABLE:
            # Use sync fallback
            return self.get(key)
            
        await self._ensure_async_connected()
        # DEV_MODE: Use in-memory fallback if Redis not connected
        if DEV_MODE and not self._is_connected_async:
            val = _in_memory_cache.get(key)
            if val is not None:
                self._hits += 1
                return val
            self._misses += 1
            return None
        try:
            val = await self._async_client.get(key)
            if val is not None:
                self._hits += 1
                return self._deserialize(val)
            self._misses += 1
            return None
        except Exception as e:
            logger.error(f"Async cache get error: {e}")
            return None

    async def set_async(self, key: str, value: Any, ttl: int = TTLPolicy.INDICATOR) -> bool:
        """Async cache set - falls back to sync if async unavailable."""
        if not REDIS_ASYNC_AVAILABLE:
            return self.set(key, value, ttl)
            
        await self._ensure_async_connected()
        # DEV_MODE: Use in-memory fallback if Redis not connected
        if DEV_MODE and not self._is_connected_async:
            _in_memory_cache[key] = value
            return True
        try:
            await self._async_client.setex(key, ttl, self._serialize(value))
            return True
        except Exception as e:
            logger.error(f"Async cache set error: {e}")
            return False

    async def mset_async(self, mapping: Dict[str, Any], ttl: int = TTLPolicy.INDICATOR) -> bool:
        """Async pipelined batch set with TTL."""
        if not REDIS_ASYNC_AVAILABLE:
            return self.mset(mapping, ttl)
            
        await self._ensure_async_connected()
        try:
            async with self._async_client.pipeline(transaction=False) as pipe:
                for key, value in mapping.items():
                    pipe.setex(key, ttl, self._serialize(value))
                await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Async mset error: {e}")
            return False

    async def publish_async(self, channel: str, message: Any) -> int:
        """Broadcast a message to a channel (Pub/Sub)."""
        if not REDIS_ASYNC_AVAILABLE: return 0
        await self._ensure_async_connected()
        try:
            return await self._async_client.publish(channel, self._serialize(message))
        except Exception as e:
            logger.error(f"PubSub publish error: {e}")
            return 0

    async def subscribe_async(self, channel: str, callback: Callable):
        """Subscribe to a channel and execute callback on messages."""
        if not REDIS_ASYNC_AVAILABLE: return
        await self._ensure_async_connected()
        try:
            pubsub = self._async_client.pubsub()
            await pubsub.subscribe(channel)
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = self._deserialize(message["data"])
                    await callback(data)
        except Exception as e:
            logger.error(f"PubSub subscribe error: {e}")

    # --- SHARED UTILS ---

    def _serialize(self, value: Any) -> str: return json.dumps(value)
    
    def _deserialize(self, value: str) -> Any:
        if value is None: return None
        try: return json.loads(value)
        except: return value

    def is_available(self) -> bool:
        return self._is_connected_sync or self._is_connected_async

    def get_stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "is_connected_sync": self._is_connected_sync,
            "is_connected_async": self._is_connected_async,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round((self._hits / total * 100) if total > 0 else 0, 2),
        }


# Singleton Accessor
_cache_manager = None

def get_cache() -> CacheManager:
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager

def cache_stats():
    return get_cache().get_stats()

# Legacy convenience function for sync cache get
def cache_get(key: str):
    """Sync cache get - for backward compatibility."""
    return get_cache().get(key)
