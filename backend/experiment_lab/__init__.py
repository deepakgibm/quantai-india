"""
Strategy Experiment Lab (Beta)
==============================
A quantitative trading experimentation module for backtesting and comparing
multiple strategy combinations using historical OHLC/OHLCV data.

⚠️ DISCLAIMER: This is for BACKTESTING & SIMULATION ONLY - No Live Trading

This module:
- Implements 70 predefined strategy combinations
- Provides comprehensive backtest metrics
- Enables multi-strategy comparison
- Works with Nifty stocks and indices
"""

from .registry import StrategyRegistry, STRATEGY_CATALOG
from .engine.backtest_runner import ExperimentRunner
from .engine.metrics_calculator import MetricsCalculator

__version__ = "1.0.0-beta"
__all__ = ["StrategyRegistry", "STRATEGY_CATALOG", "ExperimentRunner", "MetricsCalculator"]
