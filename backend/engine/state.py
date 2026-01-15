"""
In-Memory State Engine
Maintains rolling candle windows and indicator state for all symbols.
No database queries allowed in this module.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import deque
import threading
import logging

logger = logging.getLogger(__name__)

# Maximum candles to keep in memory per symbol/interval
MAX_CANDLE_WINDOW = 300


@dataclass
class Candle:
    """Single OHLCV candle."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume
        }


@dataclass
class SymbolState:
    """State for a single symbol across all intervals."""
    symbol: str
    instrument_key: str = ""
    candles: Dict[str, deque] = field(default_factory=dict)  # interval -> deque of Candle
    indicators: Dict[str, Dict[str, float]] = field(default_factory=dict)  # interval -> indicator values
    signals: Dict[str, List[str]] = field(default_factory=dict)  # interval -> active strategy signals
    last_tick: Optional[datetime] = None
    ltp: float = 0.0
    prev_close: float = 0.0
    change_pct: float = 0.0
    
    def add_candle(self, interval: str, candle: Candle) -> bool:
        """
        Add a new candle. Returns True if this is a new candle (triggers indicator update).
        """
        if interval not in self.candles:
            self.candles[interval] = deque(maxlen=MAX_CANDLE_WINDOW)
        
        # Check if this is new or update to last candle
        candle_queue = self.candles[interval]
        
        if len(candle_queue) > 0:
            last_candle = candle_queue[-1]
            if last_candle.timestamp == candle.timestamp:
                # Update existing candle (intra-bar update)
                candle_queue[-1] = candle
                return False
        
        # New candle
        candle_queue.append(candle)
        self.last_tick = candle.timestamp
        self.ltp = candle.close
        return True
    
    def get_candles(self, interval: str, count: int = 100) -> List[Candle]:
        """Get last N candles for an interval."""
        if interval not in self.candles:
            return []
        return list(self.candles[interval])[-count:]
    
    def get_closes(self, interval: str, count: int = 100) -> List[float]:
        """Get last N close prices for indicator calculation."""
        candles = self.get_candles(interval, count)
        return [c.close for c in candles]
    
    def get_volumes(self, interval: str, count: int = 100) -> List[int]:
        """Get last N volumes for indicator calculation."""
        candles = self.get_candles(interval, count)
        return [c.volume for c in candles]
    
    def set_indicators(self, interval: str, indicators: Dict[str, float]):
        """Update computed indicators for an interval."""
        self.indicators[interval] = indicators
    
    def get_indicators(self, interval: str) -> Dict[str, float]:
        """Get current indicator values for an interval."""
        return self.indicators.get(interval, {})


class StateManager:
    """
    Global in-memory state manager.
    Thread-safe singleton for managing all symbol states.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._symbols: Dict[str, SymbolState] = {}
        self._symbol_lock = threading.RLock()
        self._last_update = datetime.now()
        self._is_warmed_up = False
        self._initialized = True
        logger.info("StateManager initialized")
    
    def get_or_create_symbol(self, symbol: str, instrument_key: str = "") -> SymbolState:
        """Get or create state for a symbol."""
        with self._symbol_lock:
            if symbol not in self._symbols:
                self._symbols[symbol] = SymbolState(
                    symbol=symbol,
                    instrument_key=instrument_key
                )
            return self._symbols[symbol]
    
    def get_symbol(self, symbol: str) -> Optional[SymbolState]:
        """Get state for a symbol if it exists."""
        return self._symbols.get(symbol)
    
    def get_all_symbols(self) -> List[str]:
        """Get list of all tracked symbols."""
        return list(self._symbols.keys())
    
    def get_symbol_count(self) -> int:
        """Get count of tracked symbols."""
        return len(self._symbols)
    
    def update_from_tick(
        self,
        symbol: str,
        ltp: float,
        prev_close: float,
        instrument_key: str = ""
    ):
        """Update symbol state from a market tick (no candle yet)."""
        state = self.get_or_create_symbol(symbol, instrument_key)
        state.ltp = ltp
        state.prev_close = prev_close
        state.change_pct = ((ltp - prev_close) / prev_close * 100) if prev_close > 0 else 0.0
        state.last_tick = datetime.now()
        self._last_update = datetime.now()
    
    def add_candle(
        self,
        symbol: str,
        interval: str,
        candle: Candle,
        instrument_key: str = ""
    ) -> bool:
        """
        Add a candle to symbol state.
        Returns True if indicator recalculation is needed.
        """
        state = self.get_or_create_symbol(symbol, instrument_key)
        is_new = state.add_candle(interval, candle)
        self._last_update = datetime.now()
        return is_new
    
    def get_snapshot(self) -> List[Dict[str, Any]]:
        """Get current snapshot of all symbol states for UI."""
        snapshot = []
        for symbol, state in self._symbols.items():
            snapshot.append({
                "symbol": symbol,
                "ltp": state.ltp,
                "prev_close": state.prev_close,
                "change_pct": round(state.change_pct, 2),
                "last_tick": state.last_tick.isoformat() if state.last_tick else None,
                "indicators": state.indicators,
                "signals": state.signals
            })
        return snapshot
    
    def warm_up_from_db(self, symbols: List[str], interval: str = "1d", candle_count: int = 200):
        """
        One-time warm-up from database on service startup.
        This is the ONLY place DB access is allowed for scanner data.
        """
        if self._is_warmed_up:
            logger.info("State already warmed up, skipping")
            return
        
        logger.info(f"Warming up state for {len(symbols)} symbols, {candle_count} candles each")
        
        # Import here to avoid circular dependency
        import psycopg2
        from config import settings
        
        try:
            conn = psycopg2.connect(settings.SYNC_DATABASE_URL)
            cur = conn.cursor()
            
            for symbol in symbols:
                cur.execute("""
                    SELECT timestamp, "open", high, low, "close", volume
                    FROM stock_candles
                    WHERE symbol = %s AND timeframe = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (symbol, interval, candle_count))
                
                rows = cur.fetchall()
                
                if rows:
                    state = self.get_or_create_symbol(symbol)
                    # Rows are DESC, reverse for chronological order
                    for row in reversed(rows):
                        candle = Candle(
                            timestamp=row[0],
                            open=float(row[1]),
                            high=float(row[2]),
                            low=float(row[3]),
                            close=float(row[4]),
                            volume=int(row[5])
                        )
                        state.add_candle(interval, candle)
                    
                    # Set LTP and prev_close from most recent candles
                    if len(rows) >= 2:
                        state.ltp = float(rows[0][4])  # Most recent close
                        state.prev_close = float(rows[1][4])  # Previous close
                        state.change_pct = ((state.ltp - state.prev_close) / state.prev_close * 100) if state.prev_close > 0 else 0.0
            
            conn.close()
            self._is_warmed_up = True
            logger.info(f"Warm-up complete: {self.get_symbol_count()} symbols loaded")
            
        except Exception as e:
            logger.error(f"Warm-up failed: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get state manager status."""
        return {
            "symbol_count": self.get_symbol_count(),
            "is_warmed_up": self._is_warmed_up,
            "last_update": self._last_update.isoformat(),
            "memory_symbols": len(self._symbols)
        }


# Singleton accessor
def get_state_manager() -> StateManager:
    """Get the global state manager instance."""
    return StateManager()
