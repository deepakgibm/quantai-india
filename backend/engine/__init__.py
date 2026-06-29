"""
Engine Package
In-memory state management, indicators, MTF analysis, and background services.
"""

from engine.state import StateManager, SymbolState, Candle, get_state_manager
from engine.indicators import IndicatorEngine, IndicatorSet, compute_indicators_for_symbol
from engine.strategy_engine import (
    BaseStrategy, StrategySignal, SignalType, 
    evaluate_all_strategies, get_registered_strategies, STRATEGIES
)
# Optional imports (may not be initialized on first load)
try:
    from engine.mtf_coordinator import MTFContext, TrendAlignment, compute_mtf_context
except ImportError:
    MTFContext = None
    TrendAlignment = None
    compute_mtf_context = None

try:
    from engine.websocket_ingest import TickAggregator, get_tick_aggregator, get_ws_handler
except ImportError:
    TickAggregator = None
    get_tick_aggregator = None
    get_ws_handler = None

__all__ = [
    "StateManager",
    "SymbolState", 
    "Candle",
    "get_state_manager",
    "IndicatorEngine",
    "IndicatorSet",
    "compute_indicators_for_symbol",
    "BaseStrategy",
    "StrategySignal",
    "SignalType",
    "evaluate_all_strategies",
    "get_registered_strategies",
    "STRATEGIES",
    "MTFContext",
    "TrendAlignment",
    "compute_mtf_context",
    "TickAggregator",
    "get_tick_aggregator",
    "get_ws_handler",
]

