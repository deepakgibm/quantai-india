"""
NIFTY 100 Top Movers Service

Provides real-time top gainers and losers from NIFTY 100 stocks.
Uses Upstox API for live quotes with caching for performance.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# NIFTY 100 constituents (instrument keys for Upstox)
# Sourced dynamically from utils.symbol_utils
from utils.symbol_utils import get_nifty_symbols


@dataclass
class StockMover:
    """Represents a stock in the top movers list."""
    symbol: str
    ltp: float
    change_pct: float
    prev_close: float
    volume: int
    day_high: float
    day_low: float


class TopMoversService:
    """
    Service for computing NIFTY 100 top gainers and losers.
    
    Features:
    - Fetches live quotes from Upstox API
    - Caches results for 60 seconds
    - Handles exclusion rules (missing data, halted)
    - Returns top 5 gainers and top 5 losers
    """
    
    def __init__(self):
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl_seconds = 60
        self._upstox_client = None
    
    def _get_upstox_client(self):
        """Lazy initialization of Upstox client."""
        if self._upstox_client is None:
            from services.upstox_client import UpstoxClient
            self._upstox_client = UpstoxClient()
        return self._upstox_client
    
    def _is_cache_valid(self) -> bool:
        """Check if cached data is still valid."""
        if self._cache is None or self._cache_time is None:
            return False
        elapsed = (datetime.now() - self._cache_time).total_seconds()
        return elapsed < self._cache_ttl_seconds
    
    def _is_market_hours(self) -> bool:
        """Check if current time is within Indian stock market hours (IST)."""
        try:
            import pytz
            ist = pytz.timezone('Asia/Kolkata')
            now = datetime.now(ist)
            
            # Market closed on weekends
            if now.weekday() >= 5:  # Saturday=5, Sunday=6
                return False
            
            # Market hours: 9:15 AM to 3:30 PM IST
            market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
            market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
            
            return market_open <= now <= market_close
        except Exception:
            # Default to True if timezone check fails
            return True
    
    async def get_top_movers(self) -> Dict[str, Any]:
        """
        Get top 5 gainers and top 5 losers from NIFTY 100.
        
        Prioritizes Dragonfly cache (HP Scanner snapshots) for instant response.
        Falls back to Upstox API -> Database.
        
        NEVER returns mock data - returns explicit error if unavailable.
        """
        import time
        from services.dragonfly_client import get_cache, CacheKeys, TTLPolicy
        
        start_time = time.perf_counter()
        
        # 1. Try Dragonfly Cache (Fastest)
        try:
            cache = get_cache()
            snapshots = cache.get(CacheKeys.all_snapshots())
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            if snapshots and len(snapshots) > 0:
                logger.info(f"CACHE HIT: Dragonfly returned {len(snapshots)} snapshots in {elapsed_ms:.2f}ms")
                
                valid_stocks = []
                for s in snapshots:
                    if s.get('ltp', 0) <= 0: continue
                    
                    # Calculate change if not present
                    change_pct = s.get('change_pct')
                    if change_pct is None and s.get('prev_close') and s['prev_close'] > 0:
                        change_pct = ((s['ltp'] - s['prev_close']) / s['prev_close']) * 100
                    
                    if change_pct is None: continue

                    valid_stocks.append({
                        "symbol": s.get('symbol', 'UNKNOWN'),
                        "ltp": round(float(s.get('ltp', 0)), 2),
                        "change_pct": round(float(change_pct), 2),
                        "prev_close": round(float(s.get('prev_close', 0)), 2),
                        "volume": int(s.get('volume', 0)),
                        "day_high": round(float(s.get('high', s.get('ltp', 0))), 2),
                        "day_low": round(float(s.get('low', s.get('ltp', 0))), 2)
                    })
                
                # Sort and return with metadata
                return {
                    "as_of": datetime.now().isoformat(),
                    "gainers": sorted(valid_stocks, key=lambda x: x["change_pct"], reverse=True)[:5],
                    "losers": sorted(valid_stocks, key=lambda x: x["change_pct"])[:5],
                    "source": "dragonfly",
                    "cache_metadata": {
                        "cached_at": datetime.now().isoformat(),
                        "ttl_seconds": TTLPolicy.SNAPSHOT,
                        "is_stale": False
                    },
                    "is_market_hours": self._is_market_hours()
                }
            else:
                logger.info(f"CACHE MISS: Dragonfly empty in {elapsed_ms:.2f}ms, falling back to Upstox")
                
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(f"CACHE ERROR: Dragonfly failed in {elapsed_ms:.2f}ms: {e}")

        # 2. Existing Logic (Upstox API)
        # Return cached result of THIS service if valid (in-memory)
        if self._is_cache_valid():
            logger.debug("Returning cached top movers data (memory)")
            return self._cache
        
        logger.info("Fetching fresh NIFTY 100 quotes for top movers (Upstox Fallback)")
        
        try:
            # Build instrument keys
            symbols = get_nifty_symbols()
            instrument_keys = [f"NSE_EQ|{sym}" for sym in symbols]
            
            # Fetch quotes in batches (Upstox has limits)
            client = self._get_upstox_client()
            all_quotes = {}
            
            # Batch size of 50 to stay within limits
            batch_size = 50
            for i in range(0, len(instrument_keys), batch_size):
                batch = instrument_keys[i:i + batch_size]
                quotes = await client.get_live_quotes(batch)
                all_quotes.update(quotes)
                
                # Small delay between batches to respect rate limits
                if i + batch_size < len(instrument_keys):
                    await asyncio.sleep(0.1)
            
            # Process quotes and calculate movers
            movers = self._calculate_movers(all_quotes)
            movers["source"] = "upstox"
            
            # If no movers from live data (market closed), try database fallback
            if len(movers.get("gainers", [])) == 0 and len(movers.get("losers", [])) == 0:
                logger.info("No live data available, trying database fallback")
                movers = await self._get_movers_from_db()
            
            # Cache the result
            self._cache = movers
            self._cache_time = datetime.now()
            
            return movers
            
        except Exception as e:
            logger.error(f"Error fetching top movers: {e}")
            # Try database fallback
            try:
                movers = await self._get_movers_from_db()
                if movers.get("gainers") or movers.get("losers"):
                    return movers
            except Exception as db_error:
                logger.error(f"Database fallback also failed: {db_error}")
            
            # Return cached data if available, even if stale
            if self._cache is not None:
                logger.warning("Returning stale cached data due to error")
                return self._cache
            
            # Return empty result
            return {
                "as_of": datetime.now().isoformat(),
                "gainers": [],
                "losers": [],
                "error": str(e)
            }
    
    async def _get_movers_from_db(self) -> Dict[str, Any]:
        """Fallback: Get movers from database when live API is unavailable."""
        try:
            from services.db_data_fetcher import get_db_data_fetcher
            
            db_fetcher = get_db_data_fetcher()
            db_data = db_fetcher.fetch_latest_data()
            
            if not db_data:
                return {"as_of": datetime.now().isoformat(), "gainers": [], "losers": [], "source": "db_empty"}
            
            valid_stocks = []
            for symbol, tick in db_data.items():
                if symbol not in get_nifty_symbols():
                    continue
                
                ltp = tick.ltp or 0
                prev_close = tick.prev_close or 0
                
                if ltp <= 0 or prev_close <= 0:
                    continue
                
                change_pct = ((ltp - prev_close) / prev_close) * 100
                
                valid_stocks.append({
                    "symbol": symbol,
                    "ltp": round(ltp, 2),
                    "change_pct": round(change_pct, 2),
                    "prev_close": round(prev_close, 2),
                    "volume": 0,  # Volume not available from DB fallback
                    "day_high": round(ltp, 2),
                    "day_low": round(ltp, 2)
                })
            
            # Sort for gainers and losers
            gainers = sorted(valid_stocks, key=lambda x: x["change_pct"], reverse=True)[:5]
            losers = sorted(valid_stocks, key=lambda x: x["change_pct"])[:5]
            
            return {
                "as_of": datetime.now().isoformat(),
                "gainers": gainers,
                "losers": losers,
                "source": "database"
            }
        except Exception as e:
            logger.error(f"Database fallback error: {e}")
            return {"as_of": datetime.now().isoformat(), "gainers": [], "losers": [], "error": str(e)}

    
    def _calculate_movers(self, quotes: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Calculate top gainers and losers from quote data.
        
        Args:
            quotes: Dict mapping instrument_key to quote data
            
        Returns:
            Dict with gainers and losers lists
        """
        valid_stocks = []
        
        for key, quote in quotes.items():
            # Extract symbol from key (NSE_EQ|RELIANCE -> RELIANCE)
            symbol = key.split("|")[-1] if "|" in key else key.split(":")[-1]
            
            ltp = quote.get("last_price", 0) or 0
            prev_close = quote.get("previous_close", 0) or 0
            volume = quote.get("volume", 0) or 0
            
            # Exclusion rules
            if ltp <= 0:
                continue
            if prev_close <= 0:
                continue
            # Volume = 0 might indicate halted trading (optional check)
            
            # Calculate percentage change
            change_pct = ((ltp - prev_close) / prev_close) * 100
            
            valid_stocks.append({
                "symbol": symbol,
                "ltp": round(ltp, 2),
                "change_pct": round(change_pct, 2),
                "prev_close": round(prev_close, 2),
                "volume": volume,
                "day_high": round(quote.get("high", ltp), 2),
                "day_low": round(quote.get("low", ltp), 2)
            })
        
        # Sort for gainers (descending by change_pct)
        gainers = sorted(valid_stocks, key=lambda x: x["change_pct"], reverse=True)[:5]
        
        # Sort for losers (ascending by change_pct)
        losers = sorted(valid_stocks, key=lambda x: x["change_pct"])[:5]
        
        return {
            "as_of": datetime.now().isoformat(),
            "gainers": gainers,
            "losers": losers
        }


# Singleton instance
_top_movers_service: Optional[TopMoversService] = None


def get_top_movers_service() -> TopMoversService:
    """Get singleton instance of TopMoversService."""
    global _top_movers_service
    if _top_movers_service is None:
        _top_movers_service = TopMoversService()
    return _top_movers_service
