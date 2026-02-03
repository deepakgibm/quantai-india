import logging
from datetime import datetime
from typing import Set, List, Optional
import pytz

from services.upstox_ws_manager import get_upstox_ws_manager, UpstoxWSManager
# from services.upstox_price_resolver import get_upstox_price_resolver # MOVED to avoid circular import

logger = logging.getLogger(__name__)
IST = pytz.timezone('Asia/Kolkata')

class WebSocketFeedManager:
    """
    Manages the persistent Upstox Market Feed connection.
    Bridges the raw UpstoxWSManager with the UpstoxPriceResolver.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WebSocketFeedManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        from services.upstox_price_resolver import get_upstox_price_resolver
        self.ws_manager: UpstoxWSManager = get_upstox_ws_manager()
        self.resolver = get_upstox_price_resolver()
        self._subscribed_keys: Set[str] = set()
        self._initialized = True
        
        # Register callback
        self.ws_manager.add_callback(self._handle_tick)
        logger.info("WebSocketFeedManager: Initialized")

    def _handle_tick(self, tick: dict):
        """Process raw ticks and update caches."""
        try:
            symbol = tick.get("symbol")
            ltp = tick.get("last_price")
            
            if symbol and ltp:
                ts = datetime.now(pytz.UTC)
                prev_close = tick.get("prev_close") or tick.get("previous_close", 0)
                change_pct = tick.get("change_pct", 0)
                
                # Update resolver's high-speed local cache
                self.resolver.update_local_cache(
                    symbol=symbol,
                    ltp=ltp,
                    prev_close=prev_close,
                    change_pct=change_pct,
                    ts=ts
                )
                
                # Push to Dragonfly for global consistency
                cache = get_cache()
                if cache.is_available():
                    cache.set(f"qai:tick:{symbol}", {
                        "ltp": ltp,
                        "prev_close": prev_close,
                        "change_pct": change_pct,
                        "timestamp": ts.isoformat(),
                        "source": "UPSTOX_WS"
                    }, ttl=60) # Short TTL for live ticks
                
        except Exception as e:
            logger.error(f"FeedManager: Tick handling error: {e}")

    async def ensure_active(self, symbols: Optional[List[str]] = None):
        """Ensure WebSocket is connected and subscribed to required symbols."""
        if not self.ws_manager.is_running:
            logger.info("FeedManager: Starting Upstox WebSocket...")
            await self.ws_manager.connect()
            
        if symbols:
            new_symbols = [s for s in symbols if s.upper() not in self._subscribed_keys]
            if new_symbols:
                logger.info(f"FeedManager: Subscribing to {len(new_symbols)} new symbols")
                await self.ws_manager.subscribe(new_symbols)
                self._subscribed_keys.update([s.upper() for s in new_symbols])

    def stop(self):
        """Gracefully stop market feed."""
        self.ws_manager.stop()
        logger.info("WebSocketFeedManager: Stopped")

def get_websocket_feed_manager() -> WebSocketFeedManager:
    return WebSocketFeedManager()
