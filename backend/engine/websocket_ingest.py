"""
Upstox WebSocket Integration for In-Memory State
Receives ticks and aggregates them into candles.
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass
import json

from engine.state import get_state_manager, Candle
from engine.indicators import compute_indicators_for_symbol

logger = logging.getLogger(__name__)


@dataclass
class CandleBuilder:
    """Aggregates ticks into a candle for a specific interval."""
    symbol: str
    interval: str  # e.g., "1m", "5m", "15m"
    interval_seconds: int
    current_open: float = 0.0
    current_high: float = 0.0
    current_low: float = float('inf')
    current_close: float = 0.0
    current_volume: int = 0
    candle_start: Optional[datetime] = None
    tick_count: int = 0
    
    def add_tick(self, ltp: float, volume: int, timestamp: datetime) -> Optional[Candle]:
        """
        Add a tick to the candle builder.
        Returns a completed Candle if the interval has ended.
        """
        # Determine candle start time based on interval
        candle_start = self._get_candle_start(timestamp)
        
        # Check if we've moved to a new candle
        completed_candle = None
        if self.candle_start is not None and candle_start != self.candle_start:
            # Complete the previous candle
            if self.tick_count > 0:
                completed_candle = Candle(
                    timestamp=self.candle_start,
                    open=self.current_open,
                    high=self.current_high,
                    low=self.current_low,
                    close=self.current_close,
                    volume=self.current_volume
                )
            
            # Reset for new candle
            self._reset()
        
        # Start new candle or update current
        if self.candle_start is None:
            self.candle_start = candle_start
            self.current_open = ltp
            self.current_high = ltp
            self.current_low = ltp
        
        # Update OHLCV
        self.current_high = max(self.current_high, ltp)
        self.current_low = min(self.current_low, ltp)
        self.current_close = ltp
        self.current_volume += volume
        self.tick_count += 1
        
        return completed_candle
    
    def _get_candle_start(self, timestamp: datetime) -> datetime:
        """Get the start time of the candle containing this timestamp."""
        # Round down to nearest interval
        seconds_since_midnight = (
            timestamp.hour * 3600 + 
            timestamp.minute * 60 + 
            timestamp.second
        )
        interval_start_seconds = (seconds_since_midnight // self.interval_seconds) * self.interval_seconds
        
        return timestamp.replace(
            hour=interval_start_seconds // 3600,
            minute=(interval_start_seconds % 3600) // 60,
            second=interval_start_seconds % 60,
            microsecond=0
        )
    
    def _reset(self):
        """Reset candle builder for new candle."""
        self.current_open = 0.0
        self.current_high = 0.0
        self.current_low = float('inf')
        self.current_close = 0.0
        self.current_volume = 0
        self.candle_start = None
        self.tick_count = 0


# Interval to seconds mapping
INTERVAL_SECONDS = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "1d": 86400
}


class TickAggregator:
    """
    Aggregates market ticks into candles for multiple symbols/intervals.
    Updates the in-memory state manager.
    """
    
    def __init__(self, intervals: list = None):
        self._state_manager = get_state_manager()
        self._intervals = intervals or ["1m", "5m", "15m"]
        self._builders: Dict[str, Dict[str, CandleBuilder]] = {}  # symbol -> interval -> builder
        self._last_tick: Dict[str, datetime] = {}
        self._tick_count = 0
    
    def process_tick(
        self,
        symbol: str,
        ltp: float,
        prev_close: float,
        volume: int = 0,
        timestamp: datetime = None
    ):
        """
        Process a market tick.
        Updates state manager and builds candles.
        """
        timestamp = timestamp or datetime.now()
        
        # Update state manager with tick
        self._state_manager.update_from_tick(symbol, ltp, prev_close)
        
        # Get or create builders for this symbol
        if symbol not in self._builders:
            self._builders[symbol] = {}
            for interval in self._intervals:
                self._builders[symbol][interval] = CandleBuilder(
                    symbol=symbol,
                    interval=interval,
                    interval_seconds=INTERVAL_SECONDS.get(interval, 60)
                )
        
        # Process tick through each interval builder
        for interval, builder in self._builders[symbol].items():
            completed_candle = builder.add_tick(ltp, volume, timestamp)
            
            if completed_candle:
                # Add completed candle to state
                is_new = self._state_manager.add_candle(symbol, interval, completed_candle)
                
                if is_new:
                    # Trigger indicator recomputation
                    compute_indicators_for_symbol(symbol, interval)
        
        self._last_tick[symbol] = timestamp
        self._tick_count += 1
    
    def get_status(self) -> Dict[str, Any]:
        """Get aggregator status."""
        return {
            "tick_count": self._tick_count,
            "symbols_tracked": len(self._builders),
            "intervals": self._intervals,
            "last_ticks": {
                s: t.isoformat() for s, t in list(self._last_tick.items())[:5]
            }
        }


class WebSocketTickHandler:
    """
    Handles Upstox WebSocket messages and feeds them to the tick aggregator.
    """
    
    def __init__(self, aggregator: TickAggregator = None):
        self._aggregator = aggregator or TickAggregator()
        self._is_connected = False
        self._message_count = 0
        self._error_count = 0
    
    def handle_message(self, message: str):
        """
        Handle a WebSocket message from Upstox.
        Expected format: { "feeds": { "symbol": { "ff": { ... } } } }
        """
        try:
            data = json.loads(message) if isinstance(message, str) else message
            
            # Handle Upstox feed format
            feeds = data.get("feeds", {})
            
            for instrument_key, feed_data in feeds.items():
                full_feed = feed_data.get("ff", {})
                market_data = full_feed.get("marketFF", {})
                ltpc = market_data.get("ltpc", {})
                
                if not ltpc:
                    continue
                
                ltp = ltpc.get("ltp", 0)
                prev_close = ltpc.get("cp", ltp)
                
                # Extract volume if available
                volume = market_data.get("v", 0)
                
                # Extract symbol from instrument key (e.g., "NSE_EQ|INE001A01036")
                symbol = self._extract_symbol(instrument_key)
                
                if symbol and ltp > 0:
                    self._aggregator.process_tick(
                        symbol=symbol,
                        ltp=ltp,
                        prev_close=prev_close,
                        volume=volume
                    )
                    self._message_count += 1
                    
        except Exception as e:
            self._error_count += 1
            if self._error_count <= 10:
                logger.error(f"WebSocket message error: {e}")
    
    def _extract_symbol(self, instrument_key: str) -> Optional[str]:
        """Extract symbol from Upstox instrument key."""
        # Format: "NSE_EQ|INE001A01036" or similar
        # We need to look up the mapping from instrument key to symbol
        # For now, return the instrument key itself
        return instrument_key.split("|")[-1] if "|" in instrument_key else instrument_key
    
    def get_status(self) -> Dict[str, Any]:
        """Get handler status."""
        return {
            "is_connected": self._is_connected,
            "message_count": self._message_count,
            "error_count": self._error_count,
            "aggregator": self._aggregator.get_status()
        }


# Singleton instances
_tick_aggregator: Optional[TickAggregator] = None
_ws_handler: Optional[WebSocketTickHandler] = None


def get_tick_aggregator() -> TickAggregator:
    """Get the global tick aggregator instance."""
    global _tick_aggregator
    if _tick_aggregator is None:
        _tick_aggregator = TickAggregator()
    return _tick_aggregator


def get_ws_handler() -> WebSocketTickHandler:
    """Get the global WebSocket handler instance."""
    global _ws_handler
    if _ws_handler is None:
        _ws_handler = WebSocketTickHandler(get_tick_aggregator())
    return _ws_handler
