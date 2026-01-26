"""
Base Strategy Class for Experiment Lab
Defines the interface and common utilities for all 70 strategies.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import pandas as pd


class StrategyCategory(str, Enum):
    """Strategy category classification."""
    CATEGORY_A = "A - Single-Logic Baselines"
    CATEGORY_B = "B - Price + Momentum"
    CATEGORY_C = "C - Breakout + Filter"
    CATEGORY_D = "D - Trend + Momentum Confluence"
    CATEGORY_E = "E - Volume-Confirmed"
    CATEGORY_F = "F - Mean Reversion"
    CATEGORY_G = "G - Multi-Indicator Confluence"
    CATEGORY_H = "H - Multi-Timeframe"
    CATEGORY_I = "I - Pattern + Indicator"
    CATEGORY_J = "J - Experimental / Quant"


class SignalType(str, Enum):
    """Signal direction."""
    BUY = "BUY"
    SELL = "SELL"
    EXIT = "EXIT"
    HOLD = "HOLD"


@dataclass
class SignalResult:
    """Result from signal generation on a single bar."""
    timestamp: datetime
    signal: SignalType
    price: float
    confidence: float = 0.0  # 0.0 to 1.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    indicators: Dict[str, float] = field(default_factory=dict)
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat() if hasattr(self.timestamp, 'isoformat') else str(self.timestamp),
            "signal": self.signal.value,
            "price": round(self.price, 2),
            "confidence": round(self.confidence, 2),
            "stop_loss": round(self.stop_loss, 2) if self.stop_loss else None,
            "take_profit": round(self.take_profit, 2) if self.take_profit else None,
            "indicators": {k: round(v, 4) if isinstance(v, float) else v for k, v in self.indicators.items()},
            "reason": self.reason
        }


@dataclass
class StrategyInfo:
    """Metadata about a strategy."""
    id: int
    name: str
    category: StrategyCategory
    description: str
    indicators_used: List[str]
    min_bars_required: int = 50
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "indicators_used": self.indicators_used,
            "min_bars_required": self.min_bars_required
        }


class ExperimentStrategy(ABC):
    """
    Abstract base class for all 70 experiment strategies.
    
    Each strategy must implement:
    - info: Strategy metadata
    - generate_signals: Signal generation logic using OHLCV data
    """
    
    @property
    @abstractmethod
    def info(self) -> StrategyInfo:
        """Return strategy metadata."""
        pass
    
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> List[SignalResult]:
        """
        Generate trading signals from OHLCV data.
        
        Args:
            df: DataFrame with columns: open, high, low, close, volume
                Index should be datetime
                
        Returns:
            List of SignalResult objects for bars where signals were generated
        """
        pass
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """Validate that DataFrame has required data."""
        if df is None or len(df) < self.info.min_bars_required:
            return False
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        return all(col in df.columns for col in required_cols)
    
    def get_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        return tr.rolling(period).mean()
    
    def get_stop_loss(self, price: float, atr: float, signal: SignalType, multiplier: float = 2.0) -> float:
        """Calculate ATR-based stop loss."""
        if signal == SignalType.BUY:
            return price - (atr * multiplier)
        elif signal == SignalType.SELL:
            return price + (atr * multiplier)
        return price
    
    def get_take_profit(self, price: float, atr: float, signal: SignalType, multiplier: float = 3.0) -> float:
        """Calculate ATR-based take profit."""
        if signal == SignalType.BUY:
            return price + (atr * multiplier)
        elif signal == SignalType.SELL:
            return price - (atr * multiplier)
        return price


# Decorator for strategy registration
_strategy_registry: Dict[int, type] = {}

def register_strategy(cls):
    """Decorator to register a strategy class."""
    instance = cls()
    _strategy_registry[instance.info.id] = cls
    return cls

def get_all_strategies() -> Dict[int, type]:
    """Get all registered strategies."""
    return _strategy_registry.copy()

def get_strategy_by_id(strategy_id: int) -> Optional[type]:
    """Get a strategy class by its ID."""
    return _strategy_registry.get(strategy_id)


__all__ = [
    'StrategyCategory',
    'SignalType', 
    'SignalResult',
    'StrategyInfo',
    'ExperimentStrategy',
    'register_strategy',
    'get_all_strategies',
    'get_strategy_by_id'
]
