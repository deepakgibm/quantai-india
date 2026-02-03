"""
Strategy Engine - Base Classes and Registry
Production-grade strategy framework for equity scanning.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Type
import pandas as pd


class SignalType(str, Enum):
    """Signal direction from strategy scan."""
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"


class StrategyTier(str, Enum):
    """Strategy classification by win rate."""
    TIER_1 = "Tier 1 - Highest Win Rate"
    TIER_2 = "Tier 2 - Solid Strategies"
    TIER_3 = "Tier 3 - Advanced Strategies"
    MULTI_TF = "Multi-Timeframe Confluence"


@dataclass
class ScanResult:
    """Result from a single strategy scan on a single stock."""
    symbol: str
    index: str
    timeframe: str
    strategy: str
    signal: SignalType
    confidence_score: float  # 0.0 to 1.0
    
    # Key indicators (strategy-specific)
    indicators: Dict[str, float] = field(default_factory=dict)
    
    # Market context
    trend: str = "Unknown"
    support: Optional[float] = None
    resistance: Optional[float] = None
    volume_ratio: float = 1.0
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response format."""
        from utils.json_utils import sanitize_for_json
        
        data = {
            "symbol": self.symbol,
            "index": self.index,
            "timeframe": self.timeframe,
            "strategy": self.strategy,
            "signal": self.signal.value,
            "confidence_score": round(self.confidence_score, 2),
            "indicators": {k: round(v, 2) if isinstance(v, float) else v 
                         for k, v in self.indicators.items()},
            "trend": self.trend,
            "support": round(self.support, 2) if self.support else None,
            "resistance": round(self.resistance, 2) if self.resistance else None,
            "volume_ratio": round(self.volume_ratio, 2),
            "timestamp": self.timestamp.isoformat()
        }
        return sanitize_for_json(data)


class BaseStrategy(ABC):
    """Abstract base class for all scanning strategies."""
    
    name: str = "Base Strategy"
    description: str = "Base strategy description"
    tier: StrategyTier = StrategyTier.TIER_3
    min_bars_required: int = 50
    
    @abstractmethod
    def scan(self, df: pd.DataFrame, symbol: str, index: str, timeframe: str) -> Optional[ScanResult]:
        """Execute strategy scan on OHLCV data."""
        pass
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """Check if DataFrame has required data."""
        if df is None or len(df) < self.min_bars_required:
            return False
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        
        if not all(col in df.columns for col in required_cols):
            return False
            
        # Critical: extensive NaN check in recent data
        if df['close'].iloc[-self.min_bars_required:].isnull().any():
            return False
            
        return True
    
    def get_trend(self, df: pd.DataFrame, period: int = 20) -> str:
        """Determine trend direction using SMA."""
        if len(df) < period:
            return "Unknown"
        close = df['close'].iloc[-1]
        sma = df['close'].rolling(period).mean().iloc[-1]
        if close > sma * 1.02:
            return "Uptrend"
        elif close < sma * 0.98:
            return "Downtrend"
        return "Sideways"
    
    def get_support_resistance(self, df: pd.DataFrame, lookback: int = 20) -> tuple:
        """Calculate simple support and resistance levels."""
        if len(df) < lookback:
            return None, None
        recent = df.tail(lookback)
        return recent['low'].min(), recent['high'].max()


class StrategyRegistry:
    """Central registry for all scanning strategies."""
    
    _strategies: Dict[str, Type[BaseStrategy]] = {}
    
    @classmethod
    def register(cls, strategy_class: Type['BaseStrategy']) -> Type['BaseStrategy']:
        """Decorator to register a strategy."""
        # Use class attributes instead of instantiating
        name = getattr(strategy_class, "name", strategy_class.__name__)
        cls._strategies[name] = strategy_class
        return strategy_class
    
    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseStrategy]]:
        return cls._strategies.get(name)
    
    @classmethod
    def get_all(cls) -> Dict[str, Type[BaseStrategy]]:
        return cls._strategies.copy()
    
    @classmethod
    def list_strategies(cls) -> List[Dict[str, Any]]:
        """List all strategies with metadata."""
        result = []
        for name, strategy_cls in cls._strategies.items():
            # Use class attributes directly
            result.append({
                "name": getattr(strategy_cls, "name", name),
                "description": getattr(strategy_cls, "description", "No description"),
                "tier": getattr(strategy_cls, "tier", StrategyTier.TIER_3).value,
                "min_bars": getattr(strategy_cls, "min_bars_required", 0)
            })
        return sorted(result, key=lambda x: (x["tier"], x["name"]))


__all__ = ['SignalType', 'StrategyTier', 'ScanResult', 'BaseStrategy', 'StrategyRegistry']
