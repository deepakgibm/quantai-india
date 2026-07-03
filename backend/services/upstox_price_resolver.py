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
        
        # 1. Primary: WebSocket cache (Dragonfly)
        price_data = await self._get_ws_price(symbol)
        if price_data:
            return price_data
            
        # 2. Secondary: Upstox REST API quote
        price_data = await self._get_rest_price(symbol)
        if price_data:
            return price_data
            
        # 3. Fallback: Database EOD
        logger.info(f"Resolver: Cache and REST miss for {symbol}. Falling back to DB EOD.")
        return await self._get_db_eod_price(symbol)

    async def get_prices_bulk(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch prices for multiple symbols using optimized batch routing (Cache -> REST -> DB)."""
        if not symbols: return {}
        symbols = [s.upper() for s in symbols]
        
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
            
        # 2. Strategy: Upstox REST API Batch Fallback
        try:
            from services.upstox_client import get_upstox_client
            from services.instrument_resolver import resolve_instrument_info
            
            client = get_upstox_client()
            
            # Resolve instrument keys
            keys_to_sym = {}
            for s in pending_symbols:
                info = resolve_instrument_info(s)
                if info and info.instrument_key:
                    keys_to_sym[info.instrument_key] = s
                    
            if keys_to_sym:
                rest_res = await client.get_live_quotes(list(keys_to_sym.keys()))
                
                for inst_key, quote in rest_res.items():
                    s = keys_to_sym.get(inst_key)
                    if s and quote and quote.get("last_price"):
                        ltp = float(quote["last_price"])
                        prev_close = float(quote.get("previous_close") or ltp)
                        change_pct = float(quote.get("change_percent") or 0.0)
                        
                        res = self._format_response(
                            s, 
                            ltp, 
                            PriceSource.UPSTOX_REST, 
                            datetime.now(IST), 
                            prev_close=prev_close, 
                            change_pct=change_pct
                        )
                        results[s] = res
                        
                        # Cache it to Dragonfly (both new and legacy keys)
                        cache_key = f"price:{s}"
                        cache_key_legacy = f"qai:tick:{s}"
                        cache_payload = {
                            "symbol": s,
                            "ltp": ltp,
                            "volume": quote.get("volume", 0),
                            "prev_close": prev_close,
                            "change_percent": change_pct,
                            "timestamp": datetime.now(pytz.UTC).isoformat()
                        }
                        try:
                            await self.cache.set_async(cache_key, cache_payload, ttl=300)
                            await self.cache.set_async(cache_key_legacy, cache_payload, ttl=300)
                        except Exception as ce:
                            logger.warning(f"Resolver: Failed to write bulk REST quote to cache: {ce}")
                            
                pending_symbols = [s for s in pending_symbols if s not in results]
        except Exception as e:
            logger.error(f"Resolver: Bulk REST resolution failed: {e}")
            
        if not pending_symbols:
            return results
            
        # 3. Strategy: DB Fallback for any remaining
        try:
            from services.live_price_enricher import get_database_movers_data
            db_data = await get_database_movers_data(pending_symbols)
            
            for s in pending_symbols:
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
            logger.error(f"Resolver: Bulk EOD resolution error: {e}")
            for s in pending_symbols:
                if s not in results:
                    results[s] = await self._get_db_eod_price(s)
                    
        return results

    async def _get_ws_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Resolve price from WebSocket cache (Redis or Local Memory) with stale circuit breaker."""
        import json
        cache_key_new = f"price:{symbol}"
        cache_key_legacy = f"qai:tick:{symbol}"
        cached = None
        
        try:
            cached = await self.cache.get_async(cache_key_new)
            if not cached:
                cached = await self.cache.get_async(cache_key_legacy)
        except Exception as e:
            logger.error(f"Resolver: Cache lookup error: {e}")
            cached = None
        
        if not cached:
            # Fallback to local memory if Redis is lagging
            cached = self._local_cache.get(symbol)
            
        if cached:
            if isinstance(cached, str):
                try:
                    cached = json.loads(cached)
                except:
                    pass
                    
            ltp = cached.get("ltp") or cached.get("last_price") or cached.get("price")
            prev_close = cached.get("prev_close") or cached.get("previous_close")
            change_pct = cached.get("change_percent") or cached.get("change_pct") or 0.0
            ts_str = cached.get("timestamp")
            
            if not prev_close and ltp:
                if change_pct != 0:
                    prev_close = ltp / (1 + change_pct / 100)
                else:
                    prev_close = ltp
            
            if ltp and ts_str:
                try:
                    if isinstance(ts_str, (int, float)):
                        ts = datetime.fromtimestamp(ts_str / 1000.0, pytz.UTC)
                    else:
                        ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        
                    market_open = self.market_hours.is_market_open()
                    age = (datetime.now(pytz.UTC) - ts).total_seconds()
                    stale = market_open and (age > 5.0)
                    
                    if stale:
                        logger.warning(f"Resolver: Tick for {symbol} is stale ({age:.1f}s > 5.0s). Marking data_stale=True.")
                        
                    return self._format_response(symbol, ltp, PriceSource.UPSTOX_WS, ts, prev_close, change_pct, stale=stale)
                except Exception as e:
                    logger.warning(f"Resolver: Timestamp parse failed for {symbol}: {e}")
        
        return None

    async def _get_rest_price(self, symbol: str, is_fallback: bool = False) -> Optional[Dict[str, Any]]:
        """Fetch live quote from Upstox REST API and cache it to prevent hammering."""
        try:
            from services.upstox_client import get_upstox_client
            from services.instrument_resolver import resolve_instrument_info
            
            info = resolve_instrument_info(symbol)
            if not info or not info.instrument_key:
                return None
                
            client = get_upstox_client()
            quote = await client.get_live_quote(info.instrument_key, symbol)
            
            if quote and quote.get("last_price") and quote["last_price"] > 0:
                ltp = float(quote["last_price"])
                prev_close = float(quote.get("previous_close") or ltp)
                change_pct = float(quote.get("change_percent") or 0.0)
                
                res = self._format_response(
                    symbol, 
                    ltp, 
                    PriceSource.UPSTOX_REST, 
                    datetime.now(IST), 
                    prev_close=prev_close, 
                    change_pct=change_pct
                )
                
                # Cache to Dragonfly (both new and legacy keys)
                cache_key = f"price:{symbol}"
                cache_key_legacy = f"qai:tick:{symbol}"
                cache_payload = {
                    "symbol": symbol,
                    "ltp": ltp,
                    "volume": quote.get("volume", 0),
                    "prev_close": prev_close,
                    "change_percent": change_pct,
                    "timestamp": datetime.now(pytz.UTC).isoformat()
                }
                try:
                    await self.cache.set_async(cache_key, cache_payload, ttl=300)
                    await self.cache.set_async(cache_key_legacy, cache_payload, ttl=300)
                except Exception as ce:
                    logger.warning(f"Resolver: Failed to write REST quote to cache: {ce}")
                    
                return res
        except Exception as e:
            logger.error(f"Resolver: REST API fallback failed for {symbol}: {e}")
            
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
            "timestamp": datetime.now(IST).isoformat(),
            "stale": True,
            "data_stale": True
        }

    def _format_response(self, symbol: str, price: float, source: PriceSource, ts: datetime, prev_close: float = 0.0, change_pct: float = 0.0, stale: bool = False) -> Dict[str, Any]:
        """Ensures the Price Consistency Contract structure."""
        if ts.tzinfo is None:
            ts = IST.localize(ts)
            
        if change_pct == 0 and prev_close > 0:
            change_pct = round(((price - prev_close) / prev_close) * 100, 2)
            
        logger.info(f"Symbol={symbol} | LTP={price} | Source={source.value} | Stale={stale}")
            
        return {
            "symbol": symbol,
            "price": round(float(price or 0), 2),
            "prev_close": round(float(prev_close or 0), 2),
            "change_pct": round(float(change_pct or 0), 2),
            "is_live": source.value == PriceSource.UPSTOX_WS.value and self.market_hours.is_market_open() and not stale,
            "price_source": source.value,
            "exchange": "NSE",
            "timestamp": ts.isoformat(),
            "stale": stale,
            "data_stale": stale
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
