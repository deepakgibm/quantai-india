"""
Symbol and Strategy Metadata Cache Service

Caches frequently accessed data in DragonflyDB for fast frontend access:
- Stock symbol master data (symbol, company name, sector, instrument_key)
- Strategy definitions and metadata
- Frequently queried indicators

Features:
- Versioned cache keys for safe deployments
- Explicit TTL policies
- Cache warm-up at service startup
- Invalidation hooks on updates
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from services.dragonfly_client import get_cache, TTLPolicy, CacheUnavailableError

logger = logging.getLogger(__name__)


# =============================================================================
# Cache Key Versions (increment on schema changes)
# =============================================================================
CACHE_VERSION = "v1"


class MetadataCacheKeys:
    """Versioned cache keys for metadata."""
    PREFIX = f"qai:{CACHE_VERSION}"
    
    @staticmethod
    def symbol_master() -> str:
        """All symbols with company names and sectors."""
        return f"{MetadataCacheKeys.PREFIX}:meta:symbols"
    
    @staticmethod
    def symbol_detail(symbol: str) -> str:
        """Individual symbol details."""
        return f"{MetadataCacheKeys.PREFIX}:meta:symbol:{symbol}"
    
    @staticmethod
    def sectors() -> str:
        """List of all sectors."""
        return f"{MetadataCacheKeys.PREFIX}:meta:sectors"
    
    @staticmethod
    def sector_symbols(sector: str) -> str:
        """Symbols in a specific sector."""
        return f"{MetadataCacheKeys.PREFIX}:meta:sector:{sector}"
    
    @staticmethod
    def strategies() -> str:
        """All strategy definitions."""
        return f"{MetadataCacheKeys.PREFIX}:meta:strategies"
    
    @staticmethod
    def strategy_detail(strategy_id: str) -> str:
        """Individual strategy details."""
        return f"{MetadataCacheKeys.PREFIX}:meta:strategy:{strategy_id}"
    
    @staticmethod
    def cache_stats() -> str:
        """Cache warmup and hit/miss statistics."""
        return f"{MetadataCacheKeys.PREFIX}:meta:stats"


class MetadataCacheService:
    """
    Manages caching of symbol and strategy metadata.
    
    Usage:
        service = MetadataCacheService()
        await service.warm_cache()  # Call at startup
        
        symbols = service.get_symbol_master()  # Fast cached lookup
        strategies = service.get_strategies()   # Fast cached lookup
    """
    
    # Built-in strategy definitions (can be extended from DB)
    STRATEGIES = [
        {
            "id": "momentum",
            "name": "Momentum Scanner",
            "description": "Identifies stocks with strong price momentum using RSI, MACD, and ADX",
            "category": "technical",
            "timeframes": ["1d", "1h"],
            "indicators": ["RSI", "MACD", "ADX"],
            "risk_level": "medium"
        },
        {
            "id": "breakout",
            "name": "Breakout Detector",
            "description": "Detects price breakouts from consolidation zones using volume and resistance levels",
            "category": "technical",
            "timeframes": ["1d", "1h", "15m"],
            "indicators": ["Volume", "Bollinger Bands", "ATR"],
            "risk_level": "high"
        },
        {
            "id": "mean_reversion",
            "name": "Mean Reversion",
            "description": "Identifies overbought/oversold conditions for mean reversion trades",
            "category": "technical",
            "timeframes": ["1d"],
            "indicators": ["RSI", "Bollinger Bands", "Stochastic"],
            "risk_level": "low"
        },
        {
            "id": "trend_finder",
            "name": "AI Trend Finder",
            "description": "AI-powered trend detection combining multiple technical indicators",
            "category": "ai",
            "timeframes": ["1d"],
            "indicators": ["EMA", "MACD", "ADX", "Volume"],
            "risk_level": "medium"
        },
        {
            "id": "vwap",
            "name": "VWAP Scanner",
            "description": "Volume-weighted average price strategy for intraday trading",
            "category": "technical",
            "timeframes": ["5m", "15m", "1h"],
            "indicators": ["VWAP", "Volume", "Price"],
            "risk_level": "medium"
        },
        {
            "id": "sr_bounce",
            "name": "Support/Resistance Bounce",
            "description": "Identifies bounces from key support and resistance levels",
            "category": "technical",
            "timeframes": ["1d", "1h"],
            "indicators": ["Support", "Resistance", "Volume"],
            "risk_level": "low"
        },
        {
            "id": "week52_breakout",
            "name": "52-Week High Breakout",
            "description": "Detects stocks making new 52-week highs with volume confirmation",
            "category": "technical",
            "timeframes": ["1d"],
            "indicators": ["52W High", "Volume", "RSI"],
            "risk_level": "high"
        },
        {
            "id": "top5_picks",
            "name": "AI Top 5 Picks",
            "description": "AI-curated top 5 buy/sell recommendations based on multiple factors",
            "category": "ai",
            "timeframes": ["1d"],
            "indicators": ["Multiple"],
            "risk_level": "medium"
        }
    ]
    
    def __init__(self):
        self.cache = get_cache()
        self._warmup_timestamp: Optional[datetime] = None
        self._stats = {
            "hits": 0,
            "misses": 0,
            "last_warmup": None
        }
    
    def _load_symbols_from_db(self) -> List[Dict[str, Any]]:
        """Load symbol master from PostgreSQL using instrument_master table."""
        import psycopg2
        from config import settings
        
        try:
            # Get sync database URL
            db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            
            # Use instrument_master (new schema) instead of stock_master
            cur.execute("""
                SELECT symbol, company_name, sector, instrument_key
                FROM instrument_master
                WHERE is_active = TRUE
                ORDER BY symbol
            """)
            
            symbols = []
            for row in cur.fetchall():
                symbols.append({
                    "symbol": row[0],
                    "company_name": row[1] or row[0],
                    "sector": row[2] or "Unknown",
                    "instrument_key": row[3]
                })
            
            conn.close()
            logger.info(f"Loaded {len(symbols)} symbols from instrument_master")
            return symbols
            
        except Exception as e:
            logger.error(f"Failed to load symbols from DB: {e}")
            return []
    
    def warm_cache(self) -> Dict[str, Any]:
        """
        Pre-populate cache with symbol and strategy data.
        Call this at application startup.
        
        Returns:
            Dict with warmup statistics
        """
        logger.info("Starting metadata cache warm-up...")
        start_time = datetime.now()
        
        try:
            # 1. Load and cache symbol master
            symbols = self._load_symbols_from_db()
            if symbols:
                self.cache.set(
                    MetadataCacheKeys.symbol_master(),
                    symbols,
                    ttl=TTLPolicy.METADATA  # 1 hour
                )
                
                # 2. Build sector index
                sectors = {}
                for sym in symbols:
                    sector = sym.get("sector", "Unknown")
                    if sector not in sectors:
                        sectors[sector] = []
                    sectors[sector].append(sym["symbol"])
                
                # Cache sector list
                self.cache.set(
                    MetadataCacheKeys.sectors(),
                    list(sectors.keys()),
                    ttl=TTLPolicy.METADATA
                )
                
                # Cache symbols per sector
                for sector, sector_symbols in sectors.items():
                    self.cache.set(
                        MetadataCacheKeys.sector_symbols(sector),
                        sector_symbols,
                        ttl=TTLPolicy.METADATA
                    )
                
                # 3. Cache individual symbol details for fast lookup
                for sym in symbols:
                    self.cache.set(
                        MetadataCacheKeys.symbol_detail(sym["symbol"]),
                        sym,
                        ttl=TTLPolicy.METADATA
                    )
            
            # 4. Cache strategy definitions
            self.cache.set(
                MetadataCacheKeys.strategies(),
                self.STRATEGIES,
                ttl=TTLPolicy.METADATA
            )
            
            for strategy in self.STRATEGIES:
                self.cache.set(
                    MetadataCacheKeys.strategy_detail(strategy["id"]),
                    strategy,
                    ttl=TTLPolicy.METADATA
                )
            
            # 5. Update warmup stats
            elapsed = (datetime.now() - start_time).total_seconds()
            self._warmup_timestamp = datetime.now()
            self._stats["last_warmup"] = self._warmup_timestamp.isoformat()
            
            stats = {
                "status": "success",
                "symbols_cached": len(symbols),
                "sectors_cached": len(sectors) if symbols else 0,
                "strategies_cached": len(self.STRATEGIES),
                "elapsed_seconds": round(elapsed, 2),
                "timestamp": self._warmup_timestamp.isoformat()
            }
            
            self.cache.set(MetadataCacheKeys.cache_stats(), stats, ttl=TTLPolicy.METADATA)
            logger.info(f"Cache warm-up complete: {stats}")
            return stats
            
        except CacheUnavailableError as e:
            logger.error(f"Cache warm-up failed - DragonflyDB unavailable: {e}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Cache warm-up failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_symbol_master(self) -> List[Dict[str, Any]]:
        """Get cached symbol master data."""
        try:
            data = self.cache.get(MetadataCacheKeys.symbol_master())
            if data:
                self._stats["hits"] += 1
                return data
            else:
                self._stats["misses"] += 1
                # Fallback to DB if cache miss
                return self._load_symbols_from_db()
        except CacheUnavailableError:
            return self._load_symbols_from_db()
    
    def get_symbol_detail(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached details for a specific symbol."""
        try:
            data = self.cache.get(MetadataCacheKeys.symbol_detail(symbol))
            if data:
                self._stats["hits"] += 1
                return data
            self._stats["misses"] += 1
            return None
        except CacheUnavailableError:
            return None
    
    def get_sectors(self) -> List[str]:
        """Get cached list of sectors."""
        try:
            data = self.cache.get(MetadataCacheKeys.sectors())
            if data:
                self._stats["hits"] += 1
                return data
            self._stats["misses"] += 1
            return []
        except CacheUnavailableError:
            return []
    
    def get_sector_symbols(self, sector: str) -> List[str]:
        """Get cached symbols for a sector."""
        try:
            data = self.cache.get(MetadataCacheKeys.sector_symbols(sector))
            if data:
                self._stats["hits"] += 1
                return data
            self._stats["misses"] += 1
            return []
        except CacheUnavailableError:
            return []
    
    def get_strategies(self) -> List[Dict[str, Any]]:
        """Get cached strategy definitions."""
        try:
            data = self.cache.get(MetadataCacheKeys.strategies())
            if data:
                self._stats["hits"] += 1
                return data
            self._stats["misses"] += 1
            return self.STRATEGIES  # Fallback to built-in
        except CacheUnavailableError:
            return self.STRATEGIES
    
    def get_strategy_detail(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get cached details for a specific strategy."""
        try:
            data = self.cache.get(MetadataCacheKeys.strategy_detail(strategy_id))
            if data:
                self._stats["hits"] += 1
                return data
            self._stats["misses"] += 1
            # Fallback to built-in
            for s in self.STRATEGIES:
                if s["id"] == strategy_id:
                    return s
            return None
        except CacheUnavailableError:
            for s in self.STRATEGIES:
                if s["id"] == strategy_id:
                    return s
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate_percent": round(hit_rate, 2),
            "last_warmup": self._stats["last_warmup"],
            "cache_version": CACHE_VERSION
        }
    
    def invalidate_symbol(self, symbol: str) -> bool:
        """Invalidate cache for a specific symbol."""
        try:
            self.cache.delete(MetadataCacheKeys.symbol_detail(symbol))
            # Also invalidate master list to force refresh
            self.cache.delete(MetadataCacheKeys.symbol_master())
            logger.info(f"Invalidated cache for symbol: {symbol}")
            return True
        except CacheUnavailableError:
            return False
    
    def invalidate_all(self) -> bool:
        """Invalidate all metadata cache including sector symbols."""
        try:
            # Use pattern matching to delete ALL versioned metadata keys
            # This includes: symbols, sectors, strategies, sector symbols, symbol details
            if self.cache._client and self.cache._is_connected:
                pattern = f"{MetadataCacheKeys.PREFIX}:meta:*"
                keys = self.cache._client.keys(pattern)
                if keys:
                    self.cache._client.delete(*keys)
                    logger.info(f"Invalidated {len(keys)} metadata cache keys")
                else:
                    logger.info("No metadata cache keys to invalidate")
            else:
                # Fallback to explicit key deletion if client not accessible
                keys_to_delete = [
                    MetadataCacheKeys.symbol_master(),
                    MetadataCacheKeys.sectors(),
                    MetadataCacheKeys.strategies(),
                    MetadataCacheKeys.cache_stats()
                ]
                for key in keys_to_delete:
                    self.cache.delete(key)
                logger.info("Invalidated all metadata cache (explicit keys)")
            return True
        except CacheUnavailableError:
            return False


# =============================================================================
# Singleton Instance
# =============================================================================
_metadata_cache_service: Optional[MetadataCacheService] = None


def get_metadata_cache_service() -> MetadataCacheService:
    """Get the singleton MetadataCacheService instance."""
    global _metadata_cache_service
    if _metadata_cache_service is None:
        _metadata_cache_service = MetadataCacheService()
    return _metadata_cache_service
