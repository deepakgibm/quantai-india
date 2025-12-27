import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
from enum import Enum

class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

@dataclass
class TradeSignal:
    """Standard trade signal structure."""
    timestamp: str
    signal: SignalType
    entry_price: float
    stop_loss: float
    target_1: float
    target_2: Optional[float] = None
    confidence: float = 0.0
    reason: str = ""

@dataclass
class StrategyMetadata:
    """Strategy metadata for UI display."""
    name: str
    display_name: str
    category: str
    description: str
    parameters: Dict[str, Dict[str, Any]]
    time_horizon: str  # "Intraday", "Swing", "Positional"

class BaseStrategy(ABC):
    """Abstract base class for all strategies."""
    
    @property
    @abstractmethod
    def metadata(self) -> StrategyMetadata:
        """Return strategy metadata."""
        pass
    
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """
        Generate trading signals.
        
        Args:
            df: OHLCV DataFrame with columns [timestamp, open, high, low, close, volume]
            params: Strategy-specific parameters
            
        Returns:
            DataFrame with additional signal columns
        """
        pass
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate common indicators. Override in subclass if needed."""
        return df.copy()
