"""Strategy module init - Register all strategies."""

from .base import SignalType, StrategyTier, ScanResult, BaseStrategy, StrategyRegistry

# Import all tiers to register strategies
from .tier1 import *
from .tier2 import *
from .tier3 import *
from .multi_timeframe import *

from .registry import STRATEGIES

AVAILABLE_STRATEGIES = STRATEGIES

def list_strategies():
    """List all available strategies with metadata."""
    result = []
    for name, cls in STRATEGIES.items():
        # Use class attributes if available, otherwise defaults
        strategy_name = getattr(cls, "name", name)
        description = getattr(cls, "description", "No description available")
        result.append({
            "name": strategy_name,
            "description": description,
            "params": {} # Future: inspect init params
        })
    return result

__all__ = [
    'SignalType',
    'StrategyTier',
    'ScanResult', 
    'BaseStrategy',
    'StrategyRegistry',
    'AVAILABLE_STRATEGIES',
    'list_strategies'
]
