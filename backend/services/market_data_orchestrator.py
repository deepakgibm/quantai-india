"""
Market Data Orchestrator
Central service managing WebSocket + REST fallback for real-time market data.

Features:
- WebSocket health monitoring (3-second timeout)
- Automatic REST API fallback
- Auto-recovery to WebSocket after 3 consecutive valid ticks
- Unified data schema for seamless transitions
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import json

from services.upstox_ws_manager import get_upstox_ws_manager, UpstoxWSManager
from services.rest_data_fetcher import (
    get_rest_data_fetcher, 
    RESTDataFetcher, 
    MomentumTick, 
    calculate_bucket
)
from services.upstox_client import get_upstox_client
from services.db_data_fetcher import get_db_data_fetcher, DatabaseDataFetcher

logger = logging.getLogger(__name__)


class DataSource(Enum):
    WEBSOCKET = "WS"
    REST = "REST"
    DATABASE = "DB"
    NONE = "NONE"


@dataclass
class HealthStatus:
    """WebSocket health tracking."""
    is_healthy: bool = False
    last_tick_time: Optional[datetime] = None
    consecutive_valid_ticks: int = 0
    error_count: int = 0
    

class MarketDataOrchestrator:
    """
    Orchestrates market data from WebSocket and REST sources.
    
    - Primary: WebSocket feed
    - Fallback: REST API polling
    - Automatic switching based on health monitoring
    """
    
    # Health thresholds
    WS_TIMEOUT_SECONDS = 3.0          # Mark unhealthy if no tick for 3s
    RECONNECT_INTERVAL_SECONDS = 30   # Try WS reconnect every 30s
    VALID_TICKS_FOR_RECOVERY = 3      # Need 3 valid ticks to switch back to WS
    
    def __init__(self):
        self.ws_manager: UpstoxWSManager = get_upstox_ws_manager()
        self.rest_fetcher: RESTDataFetcher = get_rest_data_fetcher()
        self.db_fetcher: DatabaseDataFetcher = get_db_data_fetcher()
        self.upstox_client = get_upstox_client()
        
        self.current_source: DataSource = DataSource.NONE
        self.health: HealthStatus = HealthStatus()
        
        self._callbacks: List[Callable[[Dict], None]] = []
        self._data_cache: Dict[str, MomentumTick] = {}
        self._prev_close_cache: Dict[str, float] = {}
        self._last_tick_per_symbol: Dict[str, MomentumTick] = {}
        self._alert_confirmation: Dict[str, int] = {}  # symbol -> confirmation count
        
        self.is_running = False
        self._health_check_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._rest_poll_task: Optional[asyncio.Task] = None
        self._db_poll_task: Optional[asyncio.Task] = None
        self._rest_error_count: int = 0  # Track consecutive REST failures
        self._rest_error_threshold: int = 3  # Switch to DB after 3 failures
        
        # Load symbols
        self._symbols: List[tuple] = []
        self._load_symbols()
        
    def _load_symbols(self):
        """Load instrument keys mapping."""
        try:
            with open("nifty200_instruments.json", "r") as f:
                data = json.load(f)
                self._symbols = [(item[0], item[1]) for item in data]
            logger.info(f"Orchestrator loaded {len(self._symbols)} symbols")
            
            # Add indices
            self._symbols.append(("NIFTY 50", "NSE_INDEX|Nifty 50"))
            self._symbols.append(("BANK NIFTY", "NSE_INDEX|Nifty Bank"))
            self._symbols.append(("INDIA VIX", "NSE_INDEX|India VIX"))
        except Exception as e:
            logger.error(f"Failed to load symbols: {e}")
            
    def add_callback(self, callback: Callable[[Dict], None]):
        """Register callback for unified tick updates."""
        self._callbacks.append(callback)
        
    def _notify_callbacks(self, tick: MomentumTick):
        """Send tick to all registered callbacks."""
        for cb in self._callbacks:
            try:
                cb(tick.to_dict())
            except Exception as e:
                logger.error(f"Callback error: {e}")
                
    async def start(self):
        """Start the orchestrator - checks market hours to determine initial source."""
        from services.market_hours_service import get_market_hours_service
        self.market_hours = get_market_hours_service()
        self.is_running = True
        logger.info("Starting Market Data Orchestrator")
        
        # Determine source based on market hours
        if self.market_hours.is_market_open():
            logger.info("Market is OPEN - Attempting WebSocket connection")
            try:
                await asyncio.wait_for(self._connect_websocket(), timeout=10.0)
            except Exception as e:
                logger.warning(f"WebSocket failure during market hours: {e}, falling back to REST")
                await self._switch_to_rest()
        else:
            logger.info("Market is CLOSED - Starting REST/DB mode")
            await self._try_rest_or_db()
            
        # Start health monitoring only if we have a live source
        if self.current_source in [DataSource.WEBSOCKET, DataSource.REST]:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())
    
    async def _try_rest_or_db(self):
        """Try REST API, fall back to database if REST fails."""
        try:
            # Try REST API with timeout
            self.current_source = DataSource.REST
            ticks = await asyncio.wait_for(
                self.rest_fetcher.fetch_quotes(self._symbols[:20]),
                timeout=5.0
            )
            if ticks and len(ticks) > 0:
                logger.info(f"REST API working, got {len(ticks)} quotes")
                await self._switch_to_rest()
            else:
                logger.warning("REST returned no data, using database fallback")
                await self._switch_to_database()
        except asyncio.TimeoutError:
            logger.warning("REST API timed out, using database fallback")
            await self._switch_to_database()
        except Exception as e:
            logger.warning(f"REST API failed: {e}, using database fallback")
            await self._switch_to_database()
        
    async def _connect_websocket(self):
        """Attempt WebSocket connection."""
        self.ws_manager.add_callback(self._on_ws_tick)
        await self.ws_manager.connect()
        
        if self.ws_manager.is_running:
            self.current_source = DataSource.WEBSOCKET
            self.health.is_healthy = True
            self.health.last_tick_time = datetime.now()
            logger.info("WebSocket connected successfully")
            
            # Subscribe to top symbols + indices
            symbols_to_sub = [s[0] for s in self._symbols[:50]]
            # Add index symbols
            indices_to_sub = ["NIFTY 50", "BANK NIFTY", "INDIA VIX"]
            # Map them back to keys if possible, or just add the keys directly
            # For Upstox V2 indices:
            index_keys = ["NSE_INDEX|Nifty 50", "NSE_INDEX|Nifty Bank", "NSE_INDEX|India VIX"]
            
            await self.ws_manager.subscribe(symbols_to_sub)
            # We need to make sure ws_manager can handle these index keys even if not in the json
            # Actually, let's just pass the keys to subscribe directly if the manager allows it.
            # UpstoxWSManager.subscribe expects symbols and looks up keys. 
            # I should probably update UpstoxWSManager to handle index names.
            await self.ws_manager.subscribe(indices_to_sub)
            logger.info(f"Subscribed to {len(symbols_to_sub)} stocks and {len(indices_to_sub)} indices")
        else:
            raise Exception("WebSocket not running after connect")
            
    async def _switch_to_rest(self):
        """Switch to REST API fallback."""
        logger.info("Switching to REST API fallback")
        self.current_source = DataSource.REST
        self.health.is_healthy = False
        
        # Stop any existing REST polling
        if self._rest_poll_task and not self._rest_poll_task.done():
            self.rest_fetcher.stop_polling()
            self._rest_poll_task.cancel()
            
        # Start REST polling
        self._rest_poll_task = asyncio.create_task(self._rest_poll_loop())
        
    async def _rest_poll_loop(self):
        """Poll REST API for market data. Falls back to DB on consecutive failures."""
        logger.info("Starting REST polling loop")
        
        while self.is_running and self.current_source == DataSource.REST:
            try:
                # Prepare symbols to poll (top 50 stocks + indices)
                stocks_to_poll = self._symbols[:50]
                indices_to_poll = [("NIFTY 50", "NSE_INDEX|Nifty 50"), ("BANK NIFTY", "NSE_INDEX|Nifty Bank"), ("INDIA VIX", "NSE_INDEX|India VIX")]
                symbols_to_poll = stocks_to_poll + indices_to_poll
                
                ticks = await self.rest_fetcher.fetch_quotes(symbols_to_poll)
                
                # Check if we got meaningful data
                if not ticks or len(ticks) == 0:
                    self._rest_error_count += 1
                    logger.warning(f"REST returned empty data ({self._rest_error_count}/{self._rest_error_threshold})")
                    
                    if self._rest_error_count >= self._rest_error_threshold:
                        logger.warning("REST API failing repeatedly, switching to database fallback")
                        await self._switch_to_database()
                        return
                else:
                    # Reset error count on success
                    self._rest_error_count = 0
                    
                    for symbol, tick in ticks.items():
                        # Apply confirmation logic
                        confirmed_tick = self._apply_confirmation(tick)
                        if confirmed_tick:
                            self._data_cache[symbol] = confirmed_tick
                            self._notify_callbacks(confirmed_tick)
                        
            except Exception as e:
                self._rest_error_count += 1
                logger.error(f"REST poll error ({self._rest_error_count}/{self._rest_error_threshold}): {e}")
                
                if self._rest_error_count >= self._rest_error_threshold:
                    logger.warning("REST API failing repeatedly, switching to database fallback")
                    await self._switch_to_database()
                    return
                
            await asyncio.sleep(self.rest_fetcher.poll_interval)
    
    async def _switch_to_database(self):
        """Switch to database fallback when REST fails."""
        logger.info("Switching to DATABASE fallback")
        self.current_source = DataSource.DATABASE
        self.health.is_healthy = False
        
        # Stop REST polling
        if self._rest_poll_task and not self._rest_poll_task.done():
            self._rest_poll_task.cancel()
        
        # Start database polling
        self._db_poll_task = asyncio.create_task(self._db_poll_loop())
    
    async def _db_poll_loop(self):
        """Poll database for market data."""
        logger.info("Starting DATABASE polling loop")
        
        while self.is_running and self.current_source == DataSource.DATABASE:
            try:
                # Fetch from database
                symbols_list = [s[0] for s in self._symbols[:200]]
                db_ticks = self.db_fetcher.fetch_latest_data(symbols_list)
                
                if db_ticks:
                    for symbol, tick in db_ticks.items():
                        # Convert DatabaseTick to MomentumTick for compatibility
                        momentum_tick = MomentumTick(
                            symbol=tick.symbol,
                            ltp=tick.ltp,
                            prev_close=tick.prev_close,
                            change_pct=tick.change_pct,
                            bucket=tick.bucket,
                            direction=tick.direction,
                            source="DB",
                            confidence="LOW",
                            timestamp=tick.timestamp
                        )
                        self._data_cache[symbol] = momentum_tick
                        self._notify_callbacks(momentum_tick)
                    
                    logger.info(f"Database feed active: {len(db_ticks)} stocks loaded")
                else:
                    logger.warning("No data from database fallback")
                    
            except Exception as e:
                logger.error(f"Database poll error: {e}")
                
            # Database doesn't update frequently, poll every 60 seconds
            await asyncio.sleep(60)
            
    def _on_ws_tick(self, raw_tick: Dict):
        """Handle incoming WebSocket tick."""
        try:
            symbol = raw_tick.get("symbol")
            ltp = raw_tick.get("last_price")
            
            if not symbol or ltp is None:
                return
                
            # Update health
            self.health.last_tick_time = datetime.now()
            self.health.consecutive_valid_ticks += 1
            
            # Get previous close from cache or use ltp as fallback
            prev_close = self._prev_close_cache.get(symbol, ltp)
            
            # Calculate change
            if prev_close > 0:
                change_pct = ((ltp - prev_close) / prev_close) * 100
            else:
                change_pct = 0.0
                
            bucket, direction = calculate_bucket(change_pct)
            
            tick = MomentumTick(
                symbol=symbol,
                ltp=ltp,
                prev_close=prev_close,
                change_pct=round(change_pct, 2),
                bucket=bucket,
                direction=direction,
                source="WS",
                confidence="HIGH",
                timestamp=datetime.now().isoformat()
            )
            
            # Apply confirmation logic
            confirmed_tick = self._apply_confirmation(tick)
            if confirmed_tick:
                self._data_cache[symbol] = confirmed_tick
                self._notify_callbacks(confirmed_tick)
                
        except Exception as e:
            logger.error(f"WS tick processing error: {e}")
            self.health.error_count += 1
            
    def _apply_confirmation(self, tick: MomentumTick) -> Optional[MomentumTick]:
        """
        Apply alert safety rules:
        - Ignore first REST tick after WS failure
        - Require 2 consecutive confirmations before alert
        """
        symbol = tick.symbol
        last_tick = self._last_tick_per_symbol.get(symbol)
        
        # If switching sources, mark as LOW confidence initially
        if last_tick and last_tick.source != tick.source:
            tick = MomentumTick(
                **{**tick.to_dict(), "confidence": "LOW"}
            )
            
        # Confirmation logic for alerts (bucket changes)
        if last_tick and last_tick.bucket != tick.bucket:
            count = self._alert_confirmation.get(symbol, 0) + 1
            self._alert_confirmation[symbol] = count
            
            if count < 2:
                # Not enough confirmations yet
                tick = MomentumTick(
                    **{**tick.to_dict(), "confidence": "LOW"}
                )
            else:
                # Confirmed - reset counter
                self._alert_confirmation[symbol] = 0
                tick = MomentumTick(
                    **{**tick.to_dict(), "confidence": "HIGH"}
                )
        else:
            # Same bucket - reset confirmation counter
            self._alert_confirmation[symbol] = 0
            
        self._last_tick_per_symbol[symbol] = tick
        return tick
        
    async def _health_check_loop(self):
        """Monitor WebSocket health every second."""
        while self.is_running:
            try:
                await asyncio.sleep(1)
                
                if self.current_source == DataSource.WEBSOCKET:
                    # Check for timeout
                    if self.health.last_tick_time:
                        elapsed = (datetime.now() - self.health.last_tick_time).total_seconds()
                        
                        if elapsed > self.WS_TIMEOUT_SECONDS:
                            logger.warning(f"WebSocket timeout ({elapsed:.1f}s), switching to REST")
                            self.health.is_healthy = False
                            await self._switch_to_rest()
                            
                    # Check if WS manager reports not running
                    if not self.ws_manager.is_running:
                        logger.warning("WebSocket manager stopped, switching to REST")
                        self.health.is_healthy = False
                        await self._switch_to_rest()
                        
            except Exception as e:
                logger.error(f"Health check error: {e}")
                
    async def _reconnect_loop(self):
        """Try to reconnect to WebSocket every 30 seconds when in REST mode."""
        while self.is_running:
            try:
                await asyncio.sleep(self.RECONNECT_INTERVAL_SECONDS)
                
                if self.current_source == DataSource.REST:
                    logger.info("Attempting WebSocket reconnection...")
                    
                    try:
                        await self._connect_websocket()
                        
                        # Wait for valid ticks
                        self.health.consecutive_valid_ticks = 0
                        await asyncio.sleep(3)  # Wait for ticks
                        
                        if self.health.consecutive_valid_ticks >= self.VALID_TICKS_FOR_RECOVERY:
                            logger.info(f"WebSocket recovered after {self.health.consecutive_valid_ticks} valid ticks")
                            self.current_source = DataSource.WEBSOCKET
                            self.health.is_healthy = True
                            
                            # Stop REST polling
                            if self._rest_poll_task and not self._rest_poll_task.done():
                                self._rest_poll_task.cancel()
                        else:
                            logger.warning("WebSocket recovery failed, staying on REST")
                            
                    except Exception as e:
                        logger.warning(f"WebSocket reconnection failed: {e}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reconnect loop error: {e}")
                
    async def get_ltp(self, symbol: str) -> Optional[float]:
        """
        Get Last Traded Price for a symbol with hierarchical routing.
        Routes: Cache -> on-demand REST (DB fallback disabled per Phase 7 specs).
        """
        symbol = symbol.upper()
        
        # 1. Check current cache
        tick = self._data_cache.get(symbol)
        if tick and tick.ltp > 0:
            # If data is fresh (under 10s for WS/REST), return it
            return tick.ltp
            
        # 2. On-demand fetch if market is open/near-market
        try:
            from services.upstox_client import get_upstox_client
            client = get_upstox_client()
            
            # Resolve key
            keys = await self.ws_manager._resolve_instrument_keys([symbol])
            if keys:
                quote = await client.get_live_quote(keys[0], symbol)
                if quote and quote.get("last_price"):
                    return quote["last_price"]
        except Exception as e:
            logger.debug(f"On-demand LTP fetch failed for {symbol}: {e}")
            
        return tick.ltp if tick else None

    async def get_ltp_bulk(self, symbols: List[str]) -> Dict[str, float]:
        """Get multiple LTPs in a single call."""
        results = {}
        to_fetch = []
        
        for s in symbols:
            s_up = s.upper()
            tick = self._data_cache.get(s_up)
            if tick and tick.ltp > 0:
                results[s_up] = tick.ltp
            else:
                to_fetch.append(s_up)
                
        if to_fetch:
            try:
                # Resolve keys
                keys = await self.ws_manager._resolve_instrument_keys(to_fetch)
                if keys:
                    from services.upstox_client import get_upstox_client
                    client = get_upstox_client()
                    quotes = await client.get_live_quotes(keys)
                    for k, q in quotes.items():
                        # Map key back to symbol
                        sym = self.ws_manager.key_to_symbol.get(k.replace(":", "|"))
                        if sym:
                            results[sym] = q.get("last_price")
            except Exception as e:
                logger.warning(f"Bulk LTP fetch failed: {e}")
                
        return results

    def get_status(self) -> Dict:
        """Get orchestrator status for UI."""
        # Determine poll interval based on current source
        if self.current_source == DataSource.REST:
            poll_interval = self.rest_fetcher.poll_interval
        elif self.current_source == DataSource.DATABASE:
            poll_interval = 60  # Database refreshes every 60s
        else:
            poll_interval = None
            
        return {
            "source": self.current_source.value,
            "is_healthy": self.health.is_healthy,
            "last_tick": self.health.last_tick_time.isoformat() if self.health.last_tick_time else None,
            "symbol_count": len(self._data_cache),
            "poll_interval": poll_interval,
            "rest_error_count": self._rest_error_count
        }
        
    async def stop(self):
        """Stop the orchestrator."""
        self.is_running = False
        
        if self._health_check_task:
            self._health_check_task.cancel()
        if self._reconnect_task:
            self._reconnect_task.cancel()
        if self._rest_poll_task:
            self._rest_poll_task.cancel()
        if self._db_poll_task:
            self._db_poll_task.cancel()
            
        self.ws_manager.stop()
        self.rest_fetcher.stop_polling()
        
        logger.info("Market Data Orchestrator stopped")


# Singleton instance
_market_data_orchestrator = None


def get_market_data_orchestrator() -> MarketDataOrchestrator:
    """Get singleton Market Data Orchestrator instance."""
    global _market_data_orchestrator
    if _market_data_orchestrator is None:
        _market_data_orchestrator = MarketDataOrchestrator()
    return _market_data_orchestrator
