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
from backend.core.walkforward.wfa_engine import WalkForwardEngine, WFAConfig
from backend.core.legacy_strategies.ma_crossover import MACrossoverStrategy
from backend.core.quant_engine.adapters.legacy_adapter import LegacyStrategyAdapter
from backend.core.backtest.strategies_impl import StrategyRegistry

class MonteCarloSimulator:
    """Monte Carlo Simulator for trading path analysis."""
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital

    def simulate(self, returns: list, num_simulations: int = 1000, num_trades_per_path: int = 100):
        np.random.seed(42)
        paths = []
        for _ in range(num_simulations):
            path = [self.initial_capital]
            capital = self.initial_capital
            for _ in range(num_trades_per_path):
                ret = np.random.choice(returns)
                capital += ret * 100
                path.append(capital)
            paths.append(path)

        paths = np.array(paths)
        median_equity = np.median(paths, axis=0)
        upper_95 = np.percentile(paths, 95, axis=0)
        lower_5 = np.percentile(paths, 5, axis=0)
        
        max_drawdowns = []
        for path in paths:
            peaks = np.maximum.accumulate(path)
            # Avoid division by zero
            drawdowns = np.where(peaks > 0, (peaks - path) / peaks, 0)
            max_drawdowns.append(np.max(drawdowns))
            
        worst_case_drawdown = float(np.max(max_drawdowns))
        average_max_drawdown = float(np.mean(max_drawdowns))
        
        ruined = np.any(paths < (self.initial_capital * 0.8), axis=1)
        risk_of_ruin = float(np.mean(ruined))

        return {
            "risk_of_ruin_probability": risk_of_ruin,
            "median_equity": median_equity.tolist(),
            "upper_95_percentile": upper_95.tolist(),
            "lower_5_percentile": lower_5.tolist(),
            "sample_paths": paths[:5].tolist(),
            "worst_case_drawdown": worst_case_drawdown,
            "average_max_drawdown": average_max_drawdown,
            "median_final_equity": float(median_equity[-1])
        }


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
    """Verify the walk-forward engine runs IS/OOS rolling windows."""
    df = generate_mock_candles(200)
    df.set_index('timestamp', inplace=True)

    config = WFAConfig(
        symbol="RELIANCE",
        start_date=df.index.min().date(),
        end_date=df.index.max().date(),
        train_days=60,
        test_days=20,
        step_days=20,
        initial_capital=100000.0,
        optimize=False
    )

    engine = WalkForwardEngine(config)
    
    # Run the walk-forward engine
    res = engine.run(
        strategy_class=MACrossoverStrategy,
        strategy_params={"fast_period": 5, "slow_period": 10},
        data=df
    )

    assert res is not None
    assert res.strategy_name == "MACrossoverStrategy"
    assert len(res.windows) > 0
    assert res.test_return_pct is not None
    assert res.robustness_ratio is not None
    assert res.avg_sharpe is not None


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
