"""
Enhanced Base Strategy Class
Unified interface for backtesting and live trading
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import pandas as pd
from datetime import datetime


@dataclass
class Signal:
    """Trading signal from a strategy"""
    symbol: str
    action: str  # 'BUY', 'SELL', 'HOLD'
    quantity: Optional[int] = None
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: float = 1.0
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class BaseStrategy(ABC):
    """
    Base class for all trading strategies
    
    This same class is used for:
    - Backtesting
    - Walk-Forward Analysis
    - Paper Trading
    - Live Trading
    
    Ensuring consistency across all modes.
    """
    
    # Strategy metadata
    name: str = "BaseStrategy"
    version: str = "1.0.0"
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        self.params = params or {}
        self._initialized = False
    
    @abstractmethod
    def on_bar(
        self,
        bar: pd.Series,
        history: pd.DataFrame,
        positions: Dict[str, Any],
        executor: Any
    ) -> Optional[Signal]:
        """
        Called on each bar during simulation/live trading
        
        Args:
            bar: Current OHLCV bar
            history: Historical data up to current bar (no lookahead)
            positions: Current open positions
            executor: Order executor for placing orders
            
        Returns:
            Signal or None if no action
        """
        pass
    
    def on_init(self, *args, **kwargs) -> None:
        """Called once at strategy initialization"""
        self._initialized = True
    
    def on_start(self) -> None:
        """Called at the start of each trading session"""
        pass
    
    def on_end(self) -> None:
        """Called at the end of each trading session"""
        pass
    
    def get_lookback(self) -> int:
        """Return minimum bars needed for the strategy"""
        return 1
    
    def validate_params(self) -> bool:
        """Validate strategy parameters"""
        return True
    
    def get_param(self, key: str, default: Any = None) -> Any:
        """Get a parameter value with default"""
        return self.params.get(key, default)
    
    def __repr__(self) -> str:
        return f"{self.name}(v{self.version}, params={self.params})"
