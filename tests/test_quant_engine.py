"""
Unit tests for the Unified Quant Engine backend components.
Tests: LegacyStrategyAdapter, VectorizedEngine, EventDrivenEngine,
       RiskManager, MonteCarloSimulator, WalkForwardValidator.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from backend.core.quant_engine.strategy.base import UnifiedStrategy, SignalType, SignalResult
from backend.core.quant_engine.execution.vectorized import VectorizedExecutionEngine
from backend.core.quant_engine.execution.event_driven import EventDrivenExecutionEngine
from backend.core.quant_engine.metrics.calculator import UnifiedMetricsCalculator
from backend.core.quant_engine.risk.manager import UnifiedRiskManager
from backend.core.quant_engine.walk_forward.validator import WalkForwardValidator
from backend.core.quant_engine.monte_carlo.simulator import MonteCarloSimulator
from backend.core.quant_engine.adapters.legacy_adapter import LegacyStrategyAdapter
from backend.core.backtest.strategies_impl import StrategyRegistry


def generate_mock_candles(n_bars=200):
    """Generate synthetic OHLCV candle data for testing."""
    timestamps = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(n_bars)]
    np.random.seed(42)
    close_prices = 100.0 + np.cumsum(np.random.randn(n_bars))
    open_prices = close_prices - np.random.randn(n_bars) * 0.5
    high_prices = np.maximum(open_prices, close_prices) + np.random.rand(n_bars)
    low_prices = np.minimum(open_prices, close_prices) - np.random.rand(n_bars)
    volumes = np.random.randint(1000, 5000, size=n_bars)

    return pd.DataFrame({
        'timestamp': timestamps,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    })


def test_legacy_strategy_adapter_and_vectorized_engine():
    """Verify adapter wraps a legacy strategy and the vectorized engine produces valid metrics."""
    df = generate_mock_candles(100)

    # StrategyRegistry.get() returns an INSTANCE, not a class
    legacy_inst = StrategyRegistry.get("ma_crossover")
    assert legacy_inst is not None, "ma_crossover strategy must be registered"

    adapter = LegacyStrategyAdapter(legacy_inst)

    # Verify metadata delegation
    meta = adapter.metadata
    assert meta.name == "ma_crossover"

    # Preload indicators
    df_ind = adapter.preload_indicators(df)
    assert len(df_ind) == 100

    # Run vectorized engine
    vec_engine = VectorizedExecutionEngine(initial_capital=100000.0)
    vec_result = vec_engine.run(adapter, df)

    assert "total_pnl" in vec_result
    assert "sharpe_ratio" in vec_result
    assert "equity_curve" in vec_result
    assert "trades" in vec_result
    assert isinstance(vec_result["equity_curve"], list)
    assert len(vec_result["equity_curve"]) > 0


def test_legacy_strategy_adapter_and_event_driven_engine():
    """Verify adapter works with the event-driven execution engine."""
    df = generate_mock_candles(100)

    legacy_inst = StrategyRegistry.get("ma_crossover")
    assert legacy_inst is not None

    adapter = LegacyStrategyAdapter(legacy_inst)
    event_engine = EventDrivenExecutionEngine(initial_capital=100000.0)
    event_result = event_engine.run(adapter, df)

    assert "total_pnl" in event_result
    assert "sharpe_ratio" in event_result
    assert "equity_curve" in event_result
    assert "trades" in event_result


def test_metrics_calculator():
    """Verify the unified metrics calculator returns complete statistics."""
    trades = [
        {"pnl": 500, "holding_bars": 5},
        {"pnl": -200, "holding_bars": 3},
        {"pnl": 800, "holding_bars": 10},
    ]
    equity_curve = [100000, 100500, 100300, 101100]
    timestamps = ["2023-01-01", "2023-02-01", "2023-03-01", "2023-04-01"]

    result = UnifiedMetricsCalculator.calculate_performance_summary(
        trades=trades,
        equity_curve=equity_curve,
        timestamps=timestamps,
        initial_capital=100000
    )

    assert result["total_trades"] == 3
    assert result["winning_trades"] == 2
    assert result["losing_trades"] == 1
    assert result["total_pnl"] == 1100.0
    assert result["win_rate"] > 0
    assert "sharpe_ratio" in result
    assert "sortino_ratio" in result
    assert "calmar_ratio" in result
    assert "trades" in result


def test_risk_manager():
    """Verify the unified risk manager computes stops and position sizing."""
    mgr = UnifiedRiskManager()
    res = mgr.calculate_stops_and_size(
        equity=100000.0,
        price=100.0,
        risk_pct=2.0,
        risk_mode="percent_capital",
        atr=2.0
    )
    assert res["quantity"] > 0
    assert res["stop_loss"] < 100.0
    assert res["take_profit"] > 100.0


def test_monte_carlo():
    """Verify the Monte Carlo simulator produces valid simulation statistics."""
    sim = MonteCarloSimulator(initial_capital=100000.0)
    returns = [2.0, -1.0, 3.0, -2.5, 4.0, -0.5, 1.0, -1.5]
    res = sim.simulate(returns, num_simulations=50, num_trades_per_path=10)

    assert "risk_of_ruin_probability" in res
    assert "median_equity" in res
    assert "upper_95_percentile" in res
    assert "lower_5_percentile" in res
    assert "sample_paths" in res
    assert "worst_case_drawdown" in res
    assert "average_max_drawdown" in res
    assert "median_final_equity" in res

    # Median equity should have num_trades_per_path + 1 points (initial + each trade)
    assert len(res["median_equity"]) == 11
    # Sample paths should be a list of lists
    assert len(res["sample_paths"]) > 0


def test_walk_forward():
    """Verify the walk-forward validator runs IS/OOS rolling windows."""
    df = generate_mock_candles(200)

    # Get a fresh instance of the strategy via registry
    legacy_inst = StrategyRegistry.get("ma_crossover")
    assert legacy_inst is not None
    strategy_class_ref = legacy_inst.__class__

    class TestAdapter(LegacyStrategyAdapter):
        """Adapter that creates fresh legacy instances for each parameter combo."""
        def __init__(self, params=None):
            super().__init__(strategy_class_ref())

    validator = WalkForwardValidator(initial_capital=100000.0)

    # Mini parameter grid
    param_grid = [
        {"fast_period": 5, "slow_period": 10},
        {"fast_period": 8, "slow_period": 15}
    ]

    res = validator.run_walk_forward(
        strategy_class=TestAdapter,
        df=df,
        param_grid=param_grid,
        train_window_bars=60,
        test_window_bars=20,
        step_bars=20
    )

    assert "summary" in res
    assert "window_results" in res
    assert len(res["window_results"]) > 0
    assert "equity_curve" in res
    assert "validation_passed" in res
    assert "validation_messages" in res

    # Each window result should have standard fields
    win = res["window_results"][0]
    assert "window_id" in win
    assert "oos_return" in win
    assert "oos_sharpe" in win
    assert "best_parameters" in win


def test_drawdown_calculation():
    """Verify max drawdown calculation is mathematically correct."""
    equity = np.array([100, 110, 105, 108, 95, 100, 115])
    max_dd, dd_curve = UnifiedMetricsCalculator.calculate_drawdown(equity)

    # Max drawdown should be from peak 110 to trough 95 = 13.64%
    assert max_dd > 13.0
    assert max_dd < 15.0
    assert len(dd_curve) == len(equity)


def test_sharpe_ratio():
    """Verify Sharpe ratio calculation."""
    # Consistently positive returns with slight noise should give high Sharpe
    np.random.seed(99)
    returns = 0.01 + np.random.randn(252) * 0.001  # mean ~1%, tiny vol
    sharpe = UnifiedMetricsCalculator.calculate_sharpe(returns)
    assert sharpe > 1.0

    # Zero returns should give 0.0 (std is 0)
    zero_returns = np.array([0.0] * 252)
    sharpe_zero = UnifiedMetricsCalculator.calculate_sharpe(zero_returns)
    assert sharpe_zero == 0.0


def test_cagr():
    """Verify CAGR calculation."""
    cagr = UnifiedMetricsCalculator.calculate_cagr(
        initial_capital=100000,
        final_equity=200000,
        start_date="2020-01-01",
        end_date="2023-01-01"
    )
    # Doubling in 3 years ~= 26% CAGR
    assert 25.0 < cagr < 27.0
