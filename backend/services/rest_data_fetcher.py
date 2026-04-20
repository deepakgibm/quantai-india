"""
REST Data Fetcher Service
Fallback service for fetching market data via Upstox REST APIs
when WebSocket is unavailable.
"""

import asyncio
import logging
from typing import Dict, List, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import json

from services.upstox_client import get_upstox_client
import psycopg2
from config import settings
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class MomentumTick:
    """Unified data contract for momentum data from any source."""
    symbol: str
    ltp: float
    prev_close: float
    change_pct: float
    bucket: str          # "1-2%", "2-3%", "3-4%", ">4%"
    direction: str       # "Bullish" | "Bearish"
    source: str          # "WS" | "REST"
    confidence: str      # "LOW" | "HIGH"
    timestamp: str       # ISO-8601
    
    def to_dict(self) -> Dict:
        return asdict(self)


def calculate_bucket(change_pct: float) -> Tuple[str, str]:
    """Calculate momentum bucket and direction from percent change."""
    abs_change = abs(change_pct)
    
    if change_pct >= 3.0:
        bucket = "STRONG_BULLISH"
        direction = "Bullish"
    elif change_pct >= 1.5:
        bucket = "MODERATE_BULLISH"
        direction = "Bullish"
    elif change_pct <= -3.0:
        bucket = "STRONG_BEARISH"
        direction = "Bearish"
    elif change_pct <= -1.5:
        bucket = "MODERATE_BEARISH"
        direction = "Bearish"
    else:
        bucket = "NEUTRAL"
        direction = "Neutral"
    
    return bucket, direction


class RESTDataFetcher:
    """
    Fetches market data via Upstox REST APIs as fallback.
    Polls at configurable intervals based on timeframe.
    """
    
    # Polling intervals in seconds
    POLL_INTERVALS = {
        "intraday": 5,
        "15min": 10,
        "daily": 30
    }
    
    def __init__(self, timeframe: str = "intraday"):
        self.client = get_upstox_client()
        self.timeframe = timeframe
        self.poll_interval = self.POLL_INTERVALS.get(timeframe, 5)
        self.is_running = False
        self._cache: Dict[str, MomentumTick] = {}
        self._prev_close_cache: Dict[str, float] = {}
        self._callbacks: List[callable] = []
        self._symbols: List[Tuple[str, str]] = []  # (symbol, instrument_key)
        self._load_symbols()
        self._load_prev_close_from_db()
        
    def _load_symbols(self):
        """Load Nifty 200 symbols from JSON."""
        try:
            with open("nifty200_instruments.json", "r") as f:
                data = json.load(f)
                self._symbols = [(item[0], item[1]) for item in data]
            logger.info(f"REST fetcher loaded {len(self._symbols)} symbols")
            
            # Add market indices
            self._symbols.append(("NIFTY 50", "NSE_INDEX|Nifty 50"))
            self._symbols.append(("BANK NIFTY", "NSE_INDEX|Nifty Bank"))
            self._symbols.append(("INDIA VIX", "NSE_INDEX|India VIX"))
        except Exception as e:
            logger.error(f"Failed to load symbols: {e}")
            
    def _load_prev_close_from_db(self):
        """Load previous close prices from database as fallback."""
        try:
            if "postgresql" in settings.DATABASE_URL:
                result = urlparse(settings.DATABASE_URL.replace("+asyncpg", ""))
                conn = psycopg2.connect(
                    host=result.hostname or 'localhost',
                    port=result.port or 5432,
                    user=result.username or 'postgres',
                    password=result.password or 'admin',
                    database=result.path.lstrip('/') or 'quantai'
                )
            else:
                return

            cursor = conn.cursor()
            
            # Try to get latest close from stock_candle table
            # PostgreSQL syntax: using a subquery for the max timestamp
            cursor.execute("""
                SELECT symbol, close 
                FROM stock_candle 
                JOIN instrument_master ON stock_candle.instrument_id = instrument_master.instrument_id
                WHERE candle_ts = (SELECT MAX(candle_ts) FROM stock_candle)
            """)
            
            for row in cursor.fetchall():
                symbol, close = row
                if symbol and close:
                    self._prev_close_cache[symbol] = float(close)
                    
            conn.close()
            logger.info(f"Loaded {len(self._prev_close_cache)} previous close prices from database")
        except Exception as e:
            logger.warning(f"Could not load prev close from DB: {e}")

            
    def add_callback(self, callback: callable):
        """Add callback for tick updates."""
        self._callbacks.append(callback)
        
    async def fetch_quotes(self, symbols: List[Tuple[str, str]] = None) -> Dict[str, MomentumTick]:
        """
        Fetch live quotes for given symbols via REST API.
        Falls back to database previous close for change calculation.
        """
        if symbols is None:
            symbols = self._symbols[:50]  # Limit to top 50 to avoid rate limits
            
        results = {}
        
        for symbol, instrument_key in symbols:
            try:
                quote = await self.client.get_live_quote(instrument_key, symbol)
                
                if quote:
                    ltp = quote.get("last_price", 0)
                    
                    # Priority for previous close:
                    # 1. API response previous_close
                    # 2. Cached previous close (from DB or previous API call)
                    # 3. Today's close from OHLC (not ideal but better than ltp)
                    prev_close = (
                        quote.get("previous_close") or 
                        self._prev_close_cache.get(symbol) or 
                        quote.get("close") or
                        ltp  # Last resort - will result in 0% change
                    )
                    
                    # Cache previous close for future use
                    if quote.get("previous_close"):
                        self._prev_close_cache[symbol] = quote["previous_close"]
                    
                    # Calculate change percentage
                    # Use API's change_percent if available
                    change_pct = quote.get("change_percent", 0)
                    
                    # If API didn't provide change, calculate from prev_close
                    if not change_pct and prev_close and prev_close > 0 and ltp != prev_close:
                        change_pct = ((ltp - prev_close) / prev_close) * 100
                        
                    bucket, direction = calculate_bucket(change_pct)
                    
                    tick = MomentumTick(
                        symbol=symbol,
                        ltp=ltp,
                        prev_close=prev_close,
                        change_pct=round(change_pct, 2),
                        bucket=bucket,
                        direction=direction,
                        source="REST",
                        confidence="HIGH" if quote.get("previous_close") else "LOW",
                        timestamp=datetime.now().isoformat()
                    )
                    
                    results[symbol] = tick
                    self._cache[symbol] = tick
                else:
                    # Special handling for indices if Upstox fails
                    if symbol in ["NIFTY 50", "BANK NIFTY", "INDIA VIX"]:
                        try:
                            import yfinance as yf
                            yf_symbol = {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "INDIA VIX": "^INDIAVIX"}.get(symbol)
                            ticker = yf.Ticker(yf_symbol)
                            ti = ticker.info
                            ltp = ti.get('regularMarketPrice') or ti.get('previousClose') or 0
                            prev_close = ti.get('regularMarketPreviousClose') or ltp
                            
                            if ltp > 0:
                                change_pct = ((ltp - prev_close) / prev_close * 100) if prev_close > 0 else 0
                                bucket, direction = calculate_bucket(change_pct)
                                tick = MomentumTick(
                                    symbol=symbol,
                                    ltp=round(ltp, 2),
                                    prev_close=round(prev_close, 2),
                                    change_pct=round(change_pct, 2),
                                    bucket=bucket,
                                    direction=direction,
                                    source="YF",
                                    confidence="LOW",
                                    timestamp=datetime.now().isoformat()
                                )
                                results[symbol] = tick
                                self._cache[symbol] = tick
                                continue
                        except Exception as yf_e:
                            logger.warning(f"yfinance fallback failed for {symbol}: {yf_e}")

                    # API returned None - use cached or DB data
                    if symbol in self._cache:
                        results[symbol] = self._cache[symbol]
                    elif symbol in self._prev_close_cache:
                        # Create tick from DB previous close only
                        prev_close = self._prev_close_cache[symbol]
                        tick = MomentumTick(
                            symbol=symbol,
                            ltp=prev_close,  # Use prev close as current (market closed)
                            prev_close=prev_close,
                            change_pct=0.0,
                            bucket="<1%",
                            direction="Neutral",
                            source="DB",
                            confidence="LOW",
                            timestamp=datetime.now().isoformat()
                        )
                        results[symbol] = tick
                        self._cache[symbol] = tick
                    
            except Exception as e:
                logger.warning(f"Failed to fetch quote for {symbol}: {e}")
                if symbol in self._cache:
                    results[symbol] = self._cache[symbol]
                    
        return results

    
    async def start_polling(self, symbols: List[Tuple[str, str]] = None):
        """Start polling REST API at configured interval."""
        self.is_running = True
        logger.info(f"Starting REST polling at {self.poll_interval}s interval")
        
        while self.is_running:
            try:
                ticks = await self.fetch_quotes(symbols)
                
                # Notify callbacks
                for callback in self._callbacks:
                    for tick in ticks.values():
                        try:
                            callback(tick.to_dict())
                        except Exception as e:
                            logger.error(f"Callback error: {e}")
                            
            except Exception as e:
                logger.error(f"REST polling error: {e}")
                
            await asyncio.sleep(self.poll_interval)
            
    def stop_polling(self):
        """Stop the polling loop."""
        self.is_running = False
        logger.info("REST polling stopped")
        
    def get_cached_data(self) -> List[Dict]:
        """Return all cached momentum data."""
        return [tick.to_dict() for tick in self._cache.values()]


# Singleton instance
_rest_data_fetcher = None

def get_rest_data_fetcher() -> RESTDataFetcher:
    """Get singleton REST data fetcher instance."""
    global _rest_data_fetcher
    if _rest_data_fetcher is None:
        _rest_data_fetcher = RESTDataFetcher()
    return _rest_data_fetcher
