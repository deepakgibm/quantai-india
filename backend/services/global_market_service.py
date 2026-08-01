"""
Global Market Service
Fetches international market indices for after-hours context.

Provides:
- SGX Nifty (Singapore Exchange - trades when NSE closed)
- Dow Jones Industrial Average
- S&P 500
- FTSE 100 (London)
- Nasdaq Composite

Used to show market direction indicators when NSE is closed.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import yfinance as yf

from services.dragonfly_client import get_cache

logger = logging.getLogger(__name__)


@dataclass
class GlobalIndex:
    """Represents an international market index."""
    symbol: str
    name: str
    last_price: float
    change: float
    change_pct: float
    is_open: bool
    last_update: str


class GlobalMarketService:
    """
    Service to fetch and cache global market indices.
    
    Cache Strategy:
    - TTL: 5 minutes (indices update less frequently)
    - Cache key: qai:global:indices
    """
    
    INDICES = {
        "^SGX": {"name": "SGX Nifty", "trading_hours": (6, 30, 23, 30)},  # 06:30-23:30 IST
        "^DJI": {"name": "Dow Jones", "trading_hours": (19, 0, 1, 30)},   # 19:00-01:30 IST
        "^GSPC": {"name": "S&P 500", "trading_hours": (19, 0, 1, 30)},    # 19:00-01:30 IST
        "^IXIC": {"name": "Nasdaq", "trading_hours": (19, 0, 1, 30)},     # 19:00-01:30 IST
        "^FTSE": {"name": "FTSE 100", "trading_hours": (14, 30, 23, 0)},  # 14:30-23:00 IST
    }
    
    CACHE_KEY = "qai:global:indices"
    CACHE_TTL = 300  # 5 minutes
    
    def __init__(self):
        self._cache = get_cache()
        self._last_fetch: Optional[datetime] = None
    
    async def get_global_context(self) -> Dict[str, Any]:
        """
        Get global market indices with caching.
        
        Returns:
            Dict with indices data, sentiment, and metadata
        """
        # 1. Try cache first
        try:
            cached = self._cache.get(self.CACHE_KEY)
            if cached:
                logger.debug("Global indices cache hit")
                return cached
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        
        # 2. Fetch from yfinance
        logger.info("Fetching global indices from yfinance")
        indices = await self._fetch_indices()
        
        # 3. Calculate overall sentiment
        sentiment = self._calculate_sentiment(indices)
        
        result = {
            "status": "success",
            "indices": indices,
            "sentiment": sentiment,
            "timestamp": datetime.now().isoformat(),
            "is_nse_open": self._is_nse_open(),
            "cache_metadata": {
                "cached_at": datetime.now().isoformat(),
                "ttl_seconds": self.CACHE_TTL
            }
        }
        
        # 4. Cache the result
        try:
            self._cache.set(self.CACHE_KEY, result, ttl=self.CACHE_TTL)
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
        
        return result
    
    async def _fetch_indices(self) -> list:
        """Fetch all configured indices from yfinance with retry logic."""
        import httpx
        
        async def fetch_with_httpx():
            """Fallback: fetch from Yahoo Finance raw API."""
            results = []
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
                for symbol, config in self.INDICES.items():
                    try:
                        # Use Yahoo Finance v8 API
                        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
                        response = await client.get(url)
                        
                        if response.status_code != 200:
                            logger.warning(f"Yahoo API returned {response.status_code} for {symbol}")
                            continue
                        
                        data = response.json()
                        chart = data.get("chart", {}).get("result", [{}])[0]
                        meta = chart.get("meta", {})
                        quotes = chart.get("indicators", {}).get("quote", [{}])[0]
                        closes = quotes.get("close", [])
                        
                        if not closes or len(closes) < 1:
                            logger.warning(f"No price data for {symbol}")
                            continue
                        
                        # Get latest and previous close
                        last_price = closes[-1] if closes[-1] else closes[-2] if len(closes) > 1 else 0
                        prev_close = meta.get("previousClose", closes[-2] if len(closes) > 1 else last_price)
                        
                        if not last_price or not prev_close:
                            continue
                        
                        change = last_price - prev_close
                        change_pct = (change / prev_close * 100) if prev_close > 0 else 0
                        
                        is_open = self._is_index_trading(config["trading_hours"])
                        
                        results.append(asdict(GlobalIndex(
                            symbol=symbol,
                            name=config["name"],
                            last_price=round(float(last_price), 2),
                            change=round(float(change), 2),
                            change_pct=round(float(change_pct), 2),
                            is_open=is_open,
                            last_update=datetime.now().isoformat()
                        )))
                        
                    except Exception as e:
                        logger.error(f"Error fetching {symbol} via httpx: {e}")
                        continue
            
            return results
        
        # Primary: Try httpx directly (more reliable in Docker)
        try:
            indices = await fetch_with_httpx()
            if indices:
                return indices
        except Exception as e:
            logger.warning(f"httpx fetch failed: {e}")
        
        # Fallback: Try yfinance
        def fetch_sync():
            results = []
            for symbol, config in self.INDICES.items():
                try:
                    ticker = yf.Ticker(symbol)
                    # Use fast_info instead of history (more reliable)
                    info = ticker.fast_info
                    
                    last_price = info.last_price if hasattr(info, 'last_price') else 0
                    prev_close = info.previous_close if hasattr(info, 'previous_close') else 0
                    
                    if not last_price or not prev_close or last_price <= 0:
                        # Fallback to history
                        hist = ticker.history(period="2d", raise_errors=False)
                        if hist.empty or len(hist) < 1:
                            logger.warning(f"No yfinance data for {symbol}")
                            continue
                        last_price = float(hist.iloc[-1]['Close'])
                        prev_close = float(hist.iloc[-2]['Close']) if len(hist) > 1 else last_price
                    
                    change = last_price - prev_close
                    change_pct = (change / prev_close * 100) if prev_close > 0 else 0
                    
                    is_open = self._is_index_trading(config["trading_hours"])
                    
                    results.append(asdict(GlobalIndex(
                        symbol=symbol,
                        name=config["name"],
                        last_price=round(float(last_price), 2),
                        change=round(float(change), 2),
                        change_pct=round(float(change_pct), 2),
                        is_open=is_open,
                        last_update=datetime.now().isoformat()
                    )))
                    
                except Exception as e:
                    logger.error(f"Error fetching {symbol} via yfinance: {e}")
                    continue
            
            return results
        
        loop = asyncio.get_event_loop()
        indices = await loop.run_in_executor(None, fetch_sync)
        
        return indices
    
    def _is_index_trading(self, hours: tuple) -> bool:
        """Check if index is within trading hours (IST)."""
        now = datetime.now()
        start_hour, start_min, end_hour, end_min = hours
        
        current_minutes = now.hour * 60 + now.minute
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min
        
        # Handle overnight trading (e.g., US markets)
        if end_minutes < start_minutes:
            return current_minutes >= start_minutes or current_minutes <= end_minutes
        else:
            return start_minutes <= current_minutes <= end_minutes
    
    def _is_nse_open(self) -> bool:
        """Check if NSE is within trading hours."""
        now = datetime.now()
        # NSE: 09:15 - 15:30 IST, Mon-Fri
        if now.weekday() >= 5:  # Weekend
            return False
        current_minutes = now.hour * 60 + now.minute
        return 555 <= current_minutes <= 930  # 09:15 to 15:30
    
    def _calculate_sentiment(self, indices: list) -> Dict[str, Any]:
        """Calculate overall market sentiment from global indices."""
        if not indices:
            return {"direction": "NEUTRAL", "score": 0, "description": "No data available"}
        
        # Weight indices by importance
        weights = {
            "SGX Nifty": 3.0,    # Most relevant for India
            "Dow Jones": 2.0,
            "S&P 500": 2.0,
            "Nasdaq": 1.5,
            "FTSE 100": 1.0,
        }
        
        total_weight = 0
        weighted_change = 0
        
        for idx in indices:
            weight = weights.get(idx["name"], 1.0)
            weighted_change += idx["change_pct"] * weight
            total_weight += weight
        
        if total_weight == 0:
            return {"direction": "NEUTRAL", "score": 0, "description": "Insufficient data"}
        
        avg_change = weighted_change / total_weight
        
        # Determine sentiment
        if avg_change >= 1.0:
            direction = "STRONGLY_BULLISH"
            description = "Global markets showing strong positive momentum"
        elif avg_change >= 0.3:
            direction = "BULLISH"
            description = "Global markets trending positive"
        elif avg_change <= -1.0:
            direction = "STRONGLY_BEARISH"
            description = "Global markets under significant pressure"
        elif avg_change <= -0.3:
            direction = "BEARISH"
            description = "Global markets trending negative"
        else:
            direction = "NEUTRAL"
            description = "Global markets showing mixed signals"
        
        return {
            "direction": direction,
            "score": round(avg_change, 2),
            "description": description,
            "active_markets": len([i for i in indices if i["is_open"]])
        }


# =============================================================================
# Singleton Instance
# =============================================================================
_global_market_service: Optional[GlobalMarketService] = None


def get_global_market_service() -> GlobalMarketService:
    """Get the singleton GlobalMarketService instance."""
    global _global_market_service
    if _global_market_service is None:
        _global_market_service = GlobalMarketService()
    return _global_market_service
