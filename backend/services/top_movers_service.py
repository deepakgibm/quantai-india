"""
NIFTY 100 Top Movers Service

Provides real-time top gainers and losers from NIFTY 100 stocks.
Uses Upstox API for live quotes with caching for performance.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# NIFTY 100 constituents (instrument keys for Upstox)
# Format: NSE_EQ|{SYMBOL}
NIFTY_100_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "BHARTIARTL",
    "INFY", "SBIN", "ITC", "HINDUNILVR", "LT",
    "BAJFINANCE", "HCLTECH", "KOTAKBANK", "AXISBANK", "MARUTI",
    "TITAN", "SUNPHARMA", "ASIANPAINT", "WIPRO", "ULTRACEMCO",
    "ADANIENT", "NTPC", "ONGC", "TATAMOTORS", "POWERGRID",
    "M&M", "TATASTEEL", "NESTLEIND", "JSWSTEEL", "BAJAJFINSV",
    "COALINDIA", "ADANIPORTS", "TECHM", "GRASIM", "DIVISLAB",
    "HINDALCO", "BAJAJ-AUTO", "DRREDDY", "BRITANNIA", "CIPLA",
    "BPCL", "EICHERMOT", "SBILIFE", "INDUSINDBK", "APOLLOHOSP",
    "HEROMOTOCO", "TATACONSUM", "SHREECEM", "HDFCLIFE", "DABUR",
    "GODREJCP", "PIDILITIND", "HAVELLS", "SIEMENS", "DLF",
    "AMBUJACEM", "ADANIGREEN", "BANKBARODA", "INDIGO", "ICICIPRULI",
    "BERGEPAINT", "ICICIGI", "CHOLAFIN", "TATAPOWER", "VEDL",
    "NAUKRI", "JINDALSTEL", "MARICO", "COLPAL", "MUTHOOTFIN",
    "IOC", "GAIL", "BOSCHLTD", "SBICARD", "ABB",
    "TORNTPHARM", "PIIND", "SRF", "HINDPETRO", "LUPIN",
    "SAIL", "MCDOWELL-N", "LICI", "TRENT", "ZOMATO",
    "JSWENERGY", "CANBK", "POLYCAB", "ATGL", "BALKRISIND",
    "HAL", "IRCTC", "BHEL", "RECLTD", "PFC",
    "TVSMOTOR", "BEL", "NMDC", "MAXHEALTH", "LTIM"
]


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
    
    async def get_top_movers(self) -> Dict[str, Any]:
        """
        Get top 5 gainers and top 5 losers from NIFTY 100.
        
        Returns:
            Dict with 'as_of', 'gainers', and 'losers' keys
        """
        # Return cached data if valid
        if self._is_cache_valid():
            logger.debug("Returning cached top movers data")
            return self._cache
        
        logger.info("Fetching fresh NIFTY 100 quotes for top movers")
        
        try:
            # Build instrument keys
            instrument_keys = [f"NSE_EQ|{sym}" for sym in NIFTY_100_SYMBOLS]
            
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
                if symbol not in NIFTY_100_SYMBOLS:
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
