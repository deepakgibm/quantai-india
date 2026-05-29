"""
Unified Strategy Base Class
Defines the unified interface for both batch (vectorized) and event-driven backtesting.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import pandas as pd
import polars as pl
from enum import Enum


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    EXIT = "EXIT"


@dataclass
class StrategyMetadata:
    name: str
    display_name: str
    category: str
    description: str
    parameters: Dict[str, Dict[str, Any]]
    time_horizon: str  # Intraday, Swing, Positional


@dataclass
class SignalResult:
    timestamp: Any
    signal: SignalType
    price: float
    confidence: float = 1.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    indicators: Dict[str, float] = None
    reason: str = ""


class UnifiedStrategy(ABC):
    """
    Abstract base class for all strategies in the Unified Quant Engine.
    Supports both fast vectorized scanning and high-fidelity event-driven replay.
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        self.params = params or {}
        # Hydrate default parameters from metadata
        meta = self.metadata
        for key, def_val in meta.parameters.items():
            if key not in self.params:
                self.params[key] = def_val.get("default")

    @property
    @abstractmethod
    def metadata(self) -> StrategyMetadata:
        """Return strategy details and parameters schema."""
        pass

    @abstractmethod
    def preload_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute indicators over the entire DataFrame (batch/vectorized).
        Must add calculated indicators to the DataFrame columns.
        """
        pass

    @abstractmethod
    def generate_signals_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Batch signal generator for Layer 1 Fast Vectorized scans.
        Expects a DataFrame with pre-calculated indicators and adds a 'signal' column.
        """
        pass

    @abstractmethod
    def on_bar(self, bar: pd.Series, history: pd.DataFrame, positions: Dict[str, Any], executor: Any) -> Optional[SignalResult]:
        """
        Event-driven bar handler for Layer 2 simulation & live replay.
        Called on every bar index sequentially.
        """
        pass

    def evaluate_risk(self, bar: pd.Series, position: Any, risk_config: Dict[str, Any]) -> Optional[SignalResult]:
        """
        Run stop-loss or take-profit logic on the current bar.
        Defaults to basic SL/TP check; can be customized.
        """
        if not position:
            return None
            
        current_price = bar['close']
        
        # Check Stop Loss
        if position.stop_loss and current_price <= position.stop_loss:
            return SignalResult(
                timestamp=bar.name if hasattr(bar, 'name') else bar.get('timestamp'),
                signal=SignalType.EXIT,
                price=position.stop_loss,
                reason="STOP_LOSS_TRIGGERED"
            )
            
        return None

    def generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate ML features (features generation helper).
        """
        return df.copy()
