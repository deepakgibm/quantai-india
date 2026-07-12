"""
NIFTY 100 Ranking Service
Real-time Top Gainers/Losers with intelligent data sourcing.

Architecture:
- During market hours: WebSocket live ticks → In-memory → Cache every 5-10s
- After market hours: REST API EOD data → Cache with long TTL
- On startup: Cache-first strategy

Data Flow:
1. MarketHoursService determines mode (LIVE vs EOD)
2. LIVE: Subscribe to WebSocket, aggregate ticks, write to Dragonfly
3. EOD: Fetch from REST API, cache with extended TTL
4. API reads from Dragonfly cache first, computes only on cache miss
"""

import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from services.market_hours_service import get_market_hours_service
from services.dragonfly_client import get_cache, CacheKeys

logger = logging.getLogger(__name__)


# =============================================================================
# NIFTY 100 Universe
# =============================================================================
# =============================================================================
# NIFTY 100 Universe
# =============================================================================
# Now sourced dynamically from utils.symbol_utils
from utils.symbol_utils import get_nifty_symbols
from services.live_price_enricher import get_instrument_key


# =============================================================================
# Configuration
# =============================================================================
class Config:
    """Service configuration with environment variable support."""
    
    # Cache TTLs
    CACHE_TTL_LIVE = int(os.getenv("NIFTY100_CACHE_TTL_LIVE", "10"))      # During market hours
    CACHE_TTL_EOD = int(os.getenv("NIFTY100_CACHE_TTL_EOD", "18000"))     # After market (5 hours)
    
    # Refresh intervals
    REFRESH_INTERVAL = int(os.getenv("NIFTY100_REFRESH_INTERVAL", "5"))   # Seconds between cache writes
    
    # REST polling fallback
    REST_POLL_INTERVAL = 30  # Seconds between REST polls when WS fails
    
    # Reconnect settings
    MAX_RECONNECT_ATTEMPTS = 5
    RECONNECT_BASE_DELAY = 1  # Exponential backoff: 1s, 2s, 4s, 8s, 16s



@dataclass
class TickData:
    """Real-time tick data for a symbol."""
    symbol: str
    ltp: float
    prev_close: float
    change: float
    change_pct: float
    volume: int
    high: float
    low: float
    timestamp: datetime


@dataclass
class TopMoversResult:
    """Result structure for Top Gainers/Losers."""
    as_of: str
    trading_date: str
    gainers: List[Dict[str, Any]]
    losers: List[Dict[str, Any]]
    source: str
    is_market_open: bool
    cache_metadata: Optional[Dict[str, Any]] = None


class Nifty100RankingService:
    """
    Orchestrates NIFTY 100 Top Gainers/Losers calculation.
    
    Modes:
    - LIVE: Subscribe to WebSocket, update rankings in real-time
    - EOD: Fetch from REST API, cache with long TTL
    
    Cache Strategy:
    - Key: nifty100:top_gainers_losers:{trading_date}
    - LIVE TTL: 10 seconds
    - EOD TTL: 5 hours
    """
    
    def __init__(self):
        self._market_hours = get_market_hours_service()
        self._cache = get_cache()
        
        # State
        self._live_prices: Dict[str, TickData] = {}
        self._last_cache_write: Optional[datetime] = None
        self._is_running = False
        self._mode: str = "IDLE"  # LIVE, EOD, FALLBACK_REST, IDLE
        
        # Background tasks
        self._refresh_task: Optional[asyncio.Task] = None
        self._ws_manager = None
        
        # Metrics
        self._tick_count = 0
        self._cache_writes = 0
    
    # =========================================================================
    # Public API
    # =========================================================================
    
    async def start(self):
        """
        Start the ranking service based on current market status.
        
        Called at application startup and periodically to switch modes.
        """
        if self._is_running:
            logger.warning("Nifty100RankingService already running")
            return
        
        self._is_running = True
        
        # Determine mode based on market hours
        if self._market_hours.is_market_open():
            await self._start_live_mode()
        else:
            await self._start_eod_mode()
        
        # Start background task to switch modes at market open/close
        self._refresh_task = asyncio.create_task(self._mode_switch_loop())
        
        logger.info(f"Nifty100RankingService started in {self._mode} mode")
    
    async def stop(self):
        """Gracefully stop the ranking service."""
        self._is_running = False
        
        # Cancel background tasks
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect WebSocket
        if self._ws_manager:
            self._ws_manager.stop()
        
        self._mode = "IDLE"
        logger.info("Nifty100RankingService stopped")
    
    async def get_rankings(self, bypass_cache: bool = False) -> Dict[str, Any]:
        """
        Get current Top Gainers/Losers.
        
        Strategy:
        1. Try Dragonfly cache first (our own cache key, short TTL)
        2. If cache miss, explicitly fetch from PriceService (Single Source of Truth)
        
        Returns:
            TopMoversResult as dict
        """
        start_time = time.perf_counter()
        trading_date = self._market_hours.get_trading_date()
        cache_key = self._get_cache_key(trading_date)
        is_open = self._market_hours.is_market_open()
        
        # 1. Try our own cache first (short TTL ensures freshness)
        if not bypass_cache:
            try:
                cached = self._cache.get(cache_key)
                if cached:
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    logger.info(f"CACHE HIT: {cache_key} in {elapsed_ms:.2f}ms")
                    return cached
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
        
        logger.info(f"CACHE MISS (bypass={bypass_cache}): {cache_key}, fetching live data")
        
        # 2. Compute exclusively from PriceService (Single Source of Truth)
        try:
            from services.price_manager import get_price_service
            price_svc = get_price_service()
            
            nifty100_symbols = get_nifty_symbols()
            # Expanded indices list
            indices = ["NIFTY 50", "NIFTY BANK", "INDIA VIX", "FINNIFTY", "NIFTY NEXT 50", "MIDCPNIFTY"]
            symbols_to_fetch = list(set([s.upper() for s in (nifty100_symbols + indices)]))
            
            # Fetch directly from unified PriceService
            prices = await price_svc.get_prices_bulk(symbols_to_fetch)
            
            if prices and len(prices) >= 5:
                # Format data for ranking computation
                ticks = []
                for symbol, data in prices.items():
                    if data.get("ltp") and data.get("ltp") > 0:
                        ticks.append(data)
                
                if len(ticks) >= 5:
                    result = self._compute_rankings_from_resolver(ticks)
                    await self._write_to_cache(result)
                    return asdict(result)
            
            logger.warning(f"PriceService returned insufficient data ({len(prices)} symbols). Cannot compute rankings.")
        except Exception as e:
            logger.error(f"PriceService bulk fetch failed: {e}")
        
        # 3. Return empty result with error (Strict failure state)
        return {
            "as_of": datetime.now().isoformat(),
            "trading_date": str(trading_date),
            "gainers": [],
            "losers": [],
            "source": "unavailable",
            "is_market_open": is_open,
            "error": "Market data temporarily unavailable",
            "error_code": "DATA_UNAVAILABLE"
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status for monitoring."""
        return {
            "is_running": self._is_running,
            "mode": self._mode,
            "symbols_tracked": len(self._live_prices),
            "tick_count": self._tick_count,
            "cache_writes": self._cache_writes,
            "last_cache_write": self._last_cache_write.isoformat() if self._last_cache_write else None,
            "market_status": self._market_hours.get_market_status()
        }
    
    # =========================================================================
    # Mode Management
    # =========================================================================
    
    async def _start_live_mode(self):
        """Consume live data from MarketDataOrchestrator."""
        self._mode = "LIVE"
        logger.info("Starting LIVE mode - Consuming from Orchestrator")
        
        try:
            from services.websocket_feed_manager import get_websocket_feed_manager
            self._feed_manager = get_websocket_feed_manager()
            
            # Subscribe to Nifty 100 symbols via the centralized FeedManager
            symbols = get_nifty_symbols()
            await self._feed_manager.ensure_active(symbols)
            
            # Start cache refresh loop (now querying from Resolver's cache)
            asyncio.create_task(self._live_refresh_loop())
            
        except Exception as e:
            logger.error(f"Failed to start LIVE mode: {e}")
            await self._start_fallback_rest_mode()
    
    async def _start_eod_mode(self):
        """Fetch EOD data and cache with long TTL."""
        self._mode = "EOD"
        logger.info("Starting EOD mode - REST API fetch")
        
        result = await self._fetch_from_rest()
        if result:
            # Use longer TTL for EOD data
            await self._write_to_cache(result, ttl=Config.CACHE_TTL_EOD)
    
    async def _start_fallback_rest_mode(self):
        """Fallback to REST polling when WebSocket fails."""
        self._mode = "FALLBACK_REST"
        logger.warning("Starting FALLBACK_REST mode - polling every 30s")
        
        asyncio.create_task(self._rest_poll_loop())
    
    async def _mode_switch_loop(self):
        """Background loop to switch modes at market open/close."""
        while self._is_running:
            try:
                is_open = self._market_hours.is_market_open()
                
                if is_open and self._mode != "LIVE":
                    logger.info("Market opened - switching to LIVE mode")
                    await self._start_live_mode()
                    
                elif not is_open and self._mode == "LIVE":
                    logger.info("Market closed - switching to EOD mode")
                    if self._ws_manager:
                        self._ws_manager.stop()
                    await self._start_eod_mode()
                
                # Sleep for 60 seconds before next check
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Mode switch loop error: {e}")
                await asyncio.sleep(60)
    
    # =========================================================================
    # WebSocket Tick Processing
    # =========================================================================
    
    def _on_tick(self, tick: Dict[str, Any]):
        """
        Callback for WebSocket tick data.
        
        Called for every price update from Upstox WebSocket.
        Updates in-memory _live_prices dict.
        """
        try:
            symbol = tick.get("symbol") or tick.get("trading_symbol", "")
            
            # Extract symbol from instrument key if needed
            if "|" in symbol:
                symbol = symbol.split("|")[-1]
            
            # Note: We skip the NIFTY_100_SYMBOLS check here to avoid 
            # re-fetching the list on every tick. The subscription list 
            # already filters what we receive.
            
            ltp = tick.get("ltp") or tick.get("last_price", 0)
            prev_close = tick.get("prev_close") or tick.get("previous_close", 0)
            
            if ltp <= 0 or prev_close <= 0:
                return
            
            change = ltp - prev_close
            change_pct = (change / prev_close) * 100
            
            self._live_prices[symbol] = TickData(
                symbol=symbol,
                ltp=round(ltp, 2),
                prev_close=round(prev_close, 2),
                change=round(change, 2),
                change_pct=round(change_pct, 2),
                volume=tick.get("volume", 0),
                high=tick.get("high", ltp),
                low=tick.get("low", ltp),
                timestamp=datetime.now()
            )
            
            self._tick_count += 1
            
        except Exception as e:
            logger.error(f"Error processing tick: {e}")
    
    async def _live_refresh_loop(self):
        """Background loop to write rankings to cache during market hours."""
        while self._is_running and self._mode == "LIVE":
            try:
                await asyncio.sleep(Config.REFRESH_INTERVAL)
                
                from services.price_manager import get_price_service
                price_svc = get_price_service()
                
                nifty100_symbols = get_nifty_symbols()
                indices = ["NIFTY 50", "NIFTY BANK", "INDIA VIX", "FINNIFTY", "NIFTY NEXT 50", "MIDCPNIFTY"]
                symbols_to_fetch = list(set([s.upper() for s in (nifty100_symbols + indices)]))
                
                prices = await price_svc.get_prices_bulk(symbols_to_fetch)
                
                if len(prices) >= 5:
                    ticks = [data for symbol, data in prices.items() if data.get("ltp")]
                    result = self._compute_rankings_from_resolver(ticks)
                    await self._write_to_cache(result, ttl=Config.CACHE_TTL_LIVE)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Live refresh error: {e}")
    
    async def _rest_poll_loop(self):
        """Background loop for REST polling fallback."""
        while self._is_running and self._mode == "FALLBACK_REST":
            try:
                result = await self._fetch_from_rest()
                if result:
                    await self._write_to_cache(result, ttl=Config.CACHE_TTL_LIVE)
                
                await asyncio.sleep(Config.REST_POLL_INTERVAL)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"REST poll error: {e}")
    
    # =========================================================================
    # Ranking Computation
    # =========================================================================
    
    def _compute_rankings_from_resolver(self, ticks: List[Dict]) -> TopMoversResult:
        """Compute rankings from PriceService unified DTO packets."""
        valid_stocks = []
        
        for tick in ticks:
            price = tick.get("ltp", 0)
            symbol = tick.get("symbol", "UNKNOWN").upper()
            change_percent = tick.get("change_percent", 0)
            previous_close = tick.get("previous_close", 0)
            instrument_key = tick.get("instrument_key", "")
            
            # Determine segment
            segment = "EQUITY"
            if instrument_key and "INDEX" in instrument_key or symbol in ["NIFTY 50", "NIFTY BANK", "INDIA VIX", "FINNIFTY", "MIDCPNIFTY", "NIFTY NEXT 50"]:
                segment = "INDEX"
            elif instrument_key and ("F&O" in instrument_key or "NSE_FO" in instrument_key):
                segment = "F&O"
                
            # Filter out "neutral" stocks (exactly 0.0 change or no movement)
            if abs(change_percent) < 0.0001 and len(ticks) > 20:
                continue

            valid_stocks.append({
                "symbol": symbol,
                "ltp": price,
                "change_pct": round(change_percent, 4),
                "prev_close": previous_close,
                "volume": tick.get("volume", 0),
                "day_high": tick.get("high", price),
                "day_low": tick.get("low", price),
                "segment": segment
            })
        
        # Sort for gainers (descending) and losers (ascending)
        # Filter to ensure we only include positive changes in gainers and negative changes in losers
        gainers_source = [s for s in valid_stocks if s["change_pct"] > 0.0]
        losers_source = [s for s in valid_stocks if s["change_pct"] < 0.0]
        
        gainers = sorted(gainers_source, key=lambda x: x["change_pct"], reverse=True)[:10]
        losers = sorted(losers_source, key=lambda x: x["change_pct"])[:10]
        
        # Diagnostics
        missing_prev = [s["symbol"] for s in valid_stocks if s["prev_close"] <= 0]
        if missing_prev:
            logger.warning(f"Nifty100RankingService: Missing prev_close for {len(missing_prev)} symbols: {missing_prev[:5]}...")
        
        return TopMoversResult(
            as_of=datetime.now().isoformat(),
            trading_date=self._market_hours.get_trading_date(),
            gainers=gainers,
            losers=losers,
            source=f"resolver_{ticks[0].get('price_source')}" if ticks else "resolver",
            is_market_open=True,
            cache_metadata={
                "cached_at": datetime.now().isoformat(),
                "ttl_seconds": Config.CACHE_TTL_LIVE,
                "is_stale": False,
                "symbols_tracked": len(ticks)
            }
        )
    
    def _compute_rankings_from_snapshots(self, snapshots: List[Dict]) -> Optional[TopMoversResult]:
        """
        Compute rankings from HP Scanner's cached snapshots.
        
        Args:
            snapshots: List of stock snapshots from qai:snap:all cache
            
        Returns:
            TopMoversResult or None if insufficient data
        """
        valid_stocks = []
        
        for s in snapshots:
            ltp = s.get('ltp', 0)
            if ltp <= 0:
                continue
            
            # Calculate change if not present
            change_pct = s.get('change_pct')
            prev_close = s.get('prev_close', 0)
            
            if change_pct is None and prev_close and prev_close > 0:
                change_pct = ((ltp - prev_close) / prev_close) * 100
            
            if change_pct is None:
                continue
            
            valid_stocks.append({
                "symbol": s.get('symbol', 'UNKNOWN'),
                "ltp": round(float(ltp), 2),
                "change_pct": round(float(change_pct), 2),
                "prev_close": round(float(prev_close), 2) if prev_close else 0,
                "volume": int(s.get('volume', 0)),
                "day_high": round(float(s.get('high', ltp)), 2),
                "day_low": round(float(s.get('low', ltp)), 2)
            })
        
        # Validate that snapshots are from today and fresh
        is_open = self._market_hours.is_market_open()
        today_str = self._market_hours.get_trading_date() # e.g. "2026-01-05"
        now = datetime.now()
        
        # We need at least 5 stocks to make a valid ranking
        if len(valid_stocks) < 5:
            logger.warning(f"Insufficient stocks from snapshots: {len(valid_stocks)}")
            return None
            
        # Check freshness of snapshots
        first_snap = snapshots[0]
        updated_at_str = first_snap.get('updated_at')
        if updated_at_str:
            try:
                updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
                updated_at_naive = updated_at.replace(tzinfo=None)
                
                # Check 1: Date mismatch (e.g. it's Monday but data is from Friday)
                if updated_at_naive.date() < datetime.now().date():
                     logger.warning(f"Rejecting out-of-date HP Scanner cache: Data is from {updated_at_naive.date()}")
                     return None
                
                # Check 2: Stale during market hours (> 10 mins)
                if is_open and (now - updated_at_naive).total_seconds() > 600:
                    logger.warning(f"Rejecting stale HP Scanner cache: Last update {updated_at_str}")
                    return None
            except Exception as te:
                logger.warning(f"Failed to parse snapshot timestamp: {te}")
        
        # Sort for gainers (descending) and losers (ascending)
        # Filter to ensure we only include positive changes in gainers and negative changes in losers
        gainers_source = [s for s in valid_stocks if s["change_pct"] > 0.0]
        losers_source = [s for s in valid_stocks if s["change_pct"] < 0.0]
        
        gainers = sorted(gainers_source, key=lambda x: x["change_pct"], reverse=True)[:5]
        losers = sorted(losers_source, key=lambda x: x["change_pct"])[:5]
        
        is_open = self._market_hours.is_market_open()
        
        # If market is open, but we have Friday's data (e.g. Gujarat Mineral at 589),
        # we should avoid calling it "live" if it's clearly from the past.
        # But how to detect "past" without explicit date per stock?
        # We can look at the snapshot's 'updated_at' if available.
        
        return TopMoversResult(
            as_of=datetime.now().isoformat(),
            trading_date=self._market_hours.get_trading_date(),
            gainers=gainers,
            losers=losers,
            source="hp_scanner_cache",
            is_market_open=is_open,
            cache_metadata={
                "cached_at": datetime.now().isoformat(),
                "ttl_seconds": Config.CACHE_TTL_EOD if not is_open else Config.CACHE_TTL_LIVE,
                "is_stale": False,
                "symbols_from_scanner": len(valid_stocks)
            }
        )
    
    async def _fetch_from_rest(self) -> Optional[TopMoversResult]:
        """Fetch quotes from Upstox REST API."""
        try:
            from services.upstox_client import get_upstox_client
            
            client = get_upstox_client()
            
            # Build instrument keys
            nifty100_symbols = get_nifty_symbols()
            indices = ["NIFTY 50", "NIFTY BANK", "INDIA VIX", "FINNIFTY", "NIFTY NEXT 50", "MIDCPNIFTY"]
            symbols = list(set(nifty100_symbols + indices))
            
            instrument_keys = []
            for sym in symbols:
                key = get_instrument_key(sym)
                if key:
                    instrument_keys.append(key)
                if sym in ["NIFTY 50", "INDIA VIX"]:
                    logger.info(f"DEBUG: Instrument key for {sym}: {key}")
            
            # Fetch in batches using the async get_live_quotes method
            all_quotes = {}
            batch_size = 50
            
            # Fetch in batches using asyncio.gather for parallelism
            all_quotes = {}
            batch_size = 20 # Smaller batches for faster individual response
            tasks = []
            
            for i in range(0, len(instrument_keys), batch_size):
                batch = instrument_keys[i:i + batch_size]
                tasks.append(client.get_live_quotes(batch))

            # Run all batches in parallel
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for res in batch_results:
                if isinstance(res, Exception):
                    logger.warning(f"Batch fetch error: {res}")
                elif res:
                    all_quotes.update(res)
            
            if not all_quotes:
                logger.warning("REST API returned no quotes")
                return None
            
            # Process quotes
            valid_stocks = []
            for key, quote in all_quotes.items():
                # Upstox returns keys like "NSE_EQ:RELIANCE" (colon) but we send "NSE_EQ|RELIANCE" (pipe)
                # Handle both formats for symbol extraction
                if ":" in key:
                    symbol = key.split(":")[-1]
                elif "|" in key:
                    symbol = key.split("|")[-1]
                else:
                    symbol = key
                
                ltp = quote.get("last_price", 0)
                prev_close = quote.get("previous_close", 0)
                
                if ltp <= 0 or prev_close <= 0:
                    continue
                
                change_pct = ((ltp - prev_close) / prev_close) * 100
                
                # Determine segment
                segment = "EQUITY"
                if "INDEX" in key or symbol.upper() in ["NIFTY 50", "NIFTY BANK", "INDIA VIX", "FINNIFTY", "MIDCPNIFTY", "NIFTY NEXT 50"]:
                    segment = "INDEX"
                
                valid_stocks.append({
                    "symbol": symbol.upper(),
                    "ltp": round(ltp, 2),
                    "change_pct": round(change_pct, 4),
                    "prev_close": round(prev_close, 2),
                    "volume": quote.get("volume", 0),
                    "day_high": round(quote.get("high", ltp), 2),
                    "day_low": round(quote.get("low", ltp), 2),
                    "segment": segment
                })
            
            # Sort for gainers and losers
            # Filter to ensure we only include positive changes in gainers and negative changes in losers
            gainers_source = [s for s in valid_stocks if s["change_pct"] > 0.0]
            losers_source = [s for s in valid_stocks if s["change_pct"] < 0.0]
            
            gainers = sorted(gainers_source, key=lambda x: x["change_pct"], reverse=True)[:5]
            losers = sorted(losers_source, key=lambda x: x["change_pct"])[:5]
            
            is_open = self._market_hours.is_market_open()
            
            return TopMoversResult(
                as_of=datetime.now().isoformat(),
                trading_date=self._market_hours.get_trading_date(),
                gainers=gainers,
                losers=losers,
                source="rest_api",
                is_market_open=is_open,
                cache_metadata={
                    "cached_at": datetime.now().isoformat(),
                    "ttl_seconds": Config.CACHE_TTL_EOD if not is_open else Config.CACHE_TTL_LIVE,
                    "is_stale": False,
                    "symbols_fetched": len(valid_stocks)
                }
            )
            
        except Exception as e:
            logger.error(f"REST API fetch error: {e}")
            return None
    
    # =========================================================================
    # Cache Operations
    # =========================================================================
    
    def _get_cache_key(self, trading_date: str) -> str:
        """Generate cache key for the trading date."""
        return f"nifty100:top_gainers_losers:{trading_date}"
    
    async def _write_to_cache(self, result: TopMoversResult, ttl: int = None):
        """Write rankings to Dragonfly cache."""
        if ttl is None:
            ttl = Config.CACHE_TTL_LIVE if self._market_hours.is_market_open() else Config.CACHE_TTL_EOD
        
        cache_key = self._get_cache_key(result.trading_date)
        
        try:
            self._cache.set(cache_key, asdict(result), ttl=ttl)
            self._last_cache_write = datetime.now()
            self._cache_writes += 1
            
            logger.debug(f"CACHE WRITE: {cache_key} (TTL: {ttl}s)")
            
        except Exception as e:
            logger.error(f"Cache write error: {e}")


# =============================================================================
# Singleton Instance
# =============================================================================
_nifty100_ranking_service: Optional[Nifty100RankingService] = None


def get_nifty100_ranking_service() -> Nifty100RankingService:
    """Get the singleton Nifty100RankingService instance."""
    global _nifty100_ranking_service
    if _nifty100_ranking_service is None:
        _nifty100_ranking_service = Nifty100RankingService()
    return _nifty100_ranking_service


async def start_nifty100_ranking_service():
    """Start the NIFTY 100 ranking service (called at app startup)."""
    service = get_nifty100_ranking_service()
    await service.start()


async def stop_nifty100_ranking_service():
    """Stop the NIFTY 100 ranking service (called at app shutdown)."""
    service = get_nifty100_ranking_service()
    await service.stop()
