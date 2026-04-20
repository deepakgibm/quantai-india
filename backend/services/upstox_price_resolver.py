import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import pytz

from services.market_hours_service import get_market_hours_service
from services.dragonfly_client import get_cache

logger = logging.getLogger(__name__)
IST = pytz.timezone('Asia/Kolkata')

class PriceSource(Enum):
    UPSTOX_WS = "UPSTOX_WS"
    UPSTOX_REST = "UPSTOX_REST"
    UPSTOX_REST_FALLBACK = "UPSTOX_REST_FALLBACK"
    DB_EOD = "DB_EOD"
    NONE = "NONE"

class UpstoxPriceResolver:
    """
    Centralized Authority for Stock Price Resolution.
    Ensures absolute consistency across all system modules.
    """
    _instance = None
    
    # Validation Thresholds
    STALENESS_THRESHOLD_WS = 3.0    # seconds
    STALENESS_THRESHOLD_MAX = 60.0  # seconds (Mandatory: Reject > 60s)
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UpstoxPriceResolver, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.market_hours = get_market_hours_service()
        self.cache = get_cache()
        self._local_cache: Dict[str, Dict[str, Any]] = {}  # symbol -> {ltp, timestamp, source}
        self._initialized = True
        logger.info("UpstoxPriceResolver: Initialized")

    async def get_price(self, symbol: str) -> Dict[str, Any]:
        """
        Get high-precision LTP for a symbol with strict priority and resolution.
        """
        symbol = symbol.upper()
        is_market_open = self.market_hours.is_market_open()
        
        # 1. During Market Hours: Primary = WebSocket
        if is_market_open:
            # Proactively ensure feed is active for this symbol
            try:
                from services.websocket_feed_manager import get_websocket_feed_manager
                feed_manager = get_websocket_feed_manager()
                asyncio.create_task(feed_manager.ensure_active([symbol]))
            except Exception as e:
                logger.warning(f"Resolver: Failed to trigger WS feed for {symbol}: {e}")
            
            price_data = await self._get_ws_price(symbol)
            if price_data:
                return price_data
            
            # 2. Market Hours Fallback: REST API
            price_data = await self._get_rest_price(symbol, is_fallback=True)
            if price_data:
                return price_data
        
        # 3. Outside Market Hours or Double Failure: REST or DB EOD
        price_data = await self._get_rest_price(symbol, is_fallback=False)
        if price_data:
            return price_data
            
        return await self._get_db_eod_price(symbol)

    async def get_prices_bulk(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch prices for multiple symbols using optimized batch routing."""
        if not symbols: return {}
        symbols = [s.upper() for s in symbols]
        
        is_market_open = self.market_hours.is_market_open()
        results: Dict[str, Dict[str, Any]] = {}
        
        # 1. Strategy: Resolve what we can from Cache (WS)
        ws_tasks = [self._get_ws_price(s) for s in symbols]
        ws_results = await asyncio.gather(*ws_tasks)
        
        pending_symbols = []
        for i, res in enumerate(ws_results):
            if res:
                results[symbols[i]] = res
            else:
                pending_symbols.append(symbols[i])
        
        if not pending_symbols:
            return results
        
        # 2. Strategy: Use a single batch REST call for remaining
        try:
            from services.live_price_enricher import fetch_live_full_quotes
            logger.info(f"Resolver: Batch REST fetch for {len(pending_symbols)} symbols. Symbols: {pending_symbols[:10]}")
            rest_data = await fetch_live_full_quotes(pending_symbols)
            logger.info(f"Resolver: Batch REST returned {len(rest_data)} symbols. Data keys: {list(rest_data.keys())[:10]}")
            
            still_pending = []
            for s in pending_symbols:
                data = rest_data.get(s)
                if data and data.get("ltp"):
                    source = PriceSource.UPSTOX_REST_FALLBACK if is_market_open else PriceSource.UPSTOX_REST
                    results[s] = self._format_response(
                        s, 
                        data["ltp"], 
                        source, 
                        datetime.now(IST),
                        prev_close=data.get("prev_close", 0.0)
                    )
                else:
                    still_pending.append(s)
                    
            if not still_pending:
                return results
                
            # 3. Strategy: DB Fallback for any remaining
            from services.live_price_enricher import get_database_movers_data
            db_data = await get_database_movers_data(still_pending)
            
            for s in still_pending:
                data = db_data.get(s)
                if data and data.get("ltp"):
                    results[s] = self._format_response(
                        s, 
                        data["ltp"], 
                        PriceSource.DB_EOD, 
                        datetime.now(IST),
                        prev_close=data.get("prev_close", 0.0)
                    )
                else:
                    results[s] = self._format_response(s, 0.0, PriceSource.NONE, datetime.now(IST))
                    
        except Exception as e:
            logger.error(f"Resolver: Bulk resolution error: {e}")
            # Fallback to single-symbol db for safety
            for s in pending_symbols:
                if s not in results:
                    results[s] = await self._get_db_eod_price(s)
                    
        return results

    async def _get_ws_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Resolve price from WebSocket cache (Redis or Local Memory)."""
        # Priority 1: Dragonfly/Redis Cache
        cache_key = f"qai:tick:{symbol}"
        try:
            cached = await self.cache.get_async(cache_key)
        except:
            cached = None
        
        if not cached:
            # Fallback to local memory if Redis is lagging
            cached = self._local_cache.get(symbol)
            
        if cached:
            ltp = cached.get("ltp")
            prev_close = cached.get("prev_close", 0)
            change_pct = cached.get("change_pct", 0)
            ts_str = cached.get("timestamp")
            
            if ltp and ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    # Validation: Freshness Check (3 seconds)
                    age = (datetime.now(pytz.UTC) - ts).total_seconds()
                    if age <= self.STALENESS_THRESHOLD_MAX:
                        source = PriceSource.UPSTOX_WS
                        # Still warn if it exceeds the tighter WS threshold
                        if age > self.STALENESS_THRESHOLD_WS:
                            logger.warning(f"Resolver: WS tick for {symbol} is lagging ({age:.1f}s)")
                        return self._format_response(symbol, ltp, source, ts, prev_close, change_pct)
                    else:
                        logger.error(f"Resolver: REJECTED {symbol} tick - stale ({age:.1f}s > {self.STALENESS_THRESHOLD_MAX}s)")
                except Exception as e:
                    logger.warning(f"Resolver: Timestamp parse failed for {symbol}: {e}")
        
        return None

    async def _get_rest_price(self, symbol: str, is_fallback: bool = False) -> Optional[Dict[str, Any]]:
        """Resolve price from Upstox REST API with full quote support."""
        try:
            from services.live_price_enricher import fetch_live_full_quotes
            quotes = await fetch_live_full_quotes([symbol])
            data = quotes.get(symbol)
            
            if data and data.get("ltp"):
                source = PriceSource.UPSTOX_REST_FALLBACK if is_fallback else PriceSource.UPSTOX_REST
                return self._format_response(
                    symbol, 
                    data["ltp"], 
                    source, 
                    datetime.now(IST),
                    prev_close=data.get("prev_close", 0.0)
                )
        except Exception as e:
            logger.error(f"Resolver: REST fetch failed for {symbol}: {e}")
        return None

    async def _get_db_eod_price(self, symbol: str) -> Dict[str, Any]:
        """Resolve price from database as a final EOD fallback with prev_close support."""
        try:
            from services.live_price_enricher import get_database_movers_data
            data_map = await get_database_movers_data([symbol])
            data = data_map.get(symbol)
            
            if data and data.get("ltp"):
                return self._format_response(
                    symbol, 
                    data["ltp"], 
                    PriceSource.DB_EOD, 
                    datetime.now(IST),
                    prev_close=data.get("prev_close", 0.0)
                )
        except Exception as e:
            logger.error(f"Resolver: DB fallback failed for {symbol}: {e}")
            
        return {
            "symbol": symbol,
            "price": 0.0,
            "prev_close": 0.0,
            "change_pct": 0.0,
            "is_live": False,
            "price_source": PriceSource.NONE.value,
            "exchange": "NSE",
            "timestamp": datetime.now(IST).isoformat()
        }

    def _format_response(self, symbol: str, price: float, source: PriceSource, ts: datetime, prev_close: float = 0.0, change_pct: float = 0.0) -> Dict[str, Any]:
        """Ensures the Price Consistency Contract structure."""
        if ts.tzinfo is None:
            ts = IST.localize(ts)
            
        # If change_pct is 0 but we have prev_close, calculate it
        if change_pct == 0 and prev_close > 0:
            change_pct = round(((price - prev_close) / prev_close) * 100, 2)
            
        return {
            "symbol": symbol,
            "price": round(float(price or 0), 2),
            "prev_close": round(float(prev_close or 0), 2),
            "change_pct": round(float(change_pct or 0), 2),
            "is_live": source.value in [PriceSource.UPSTOX_WS.value, PriceSource.UPSTOX_REST.value, PriceSource.UPSTOX_REST_FALLBACK.value],
            "price_source": source.value,
            "exchange": "NSE",
            "timestamp": ts.isoformat()
        }

    def update_local_cache(self, symbol: str, ltp: float, ts: datetime, prev_close: float = 0.0, change_pct: float = 0.0):
        """Called by WebSocketFeedManager to update sub-second local lookups."""
        self._local_cache[symbol] = {
            "ltp": ltp,
            "prev_close": prev_close,
            "change_pct": change_pct,
            "timestamp": ts.isoformat(),
            "source": PriceSource.UPSTOX_WS.value
        }

# Singleton accessor
def get_upstox_price_resolver() -> UpstoxPriceResolver:
    return UpstoxPriceResolver()
