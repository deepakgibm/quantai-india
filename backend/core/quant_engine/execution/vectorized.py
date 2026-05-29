"""
Layer 1: Fast Vectorized Execution Engine
Optimized for parameter sweeps and quick scans.
"""

import numpy as np
import pandas as pd
import polars as pl
from typing import Dict, Any, List, Optional
import time

from ..strategy.base import UnifiedStrategy, SignalType
from ..metrics.calculator import UnifiedMetricsCalculator


class VectorizedExecutionEngine:
    """
    High-performance backtesting using vectorized Pandas and Polars logic.
    Ideal for testing large batches of parameters.
    """

    def __init__(self, initial_capital: float = 1000000.0):
        self.initial_capital = initial_capital

    def run(self, strategy: UnifiedStrategy, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Runs a vectorized strategy backtest.
        
        Args:
            strategy: UnifiedStrategy instance
            df: Raw OHLCV DataFrame
            
        Returns:
            Dict containing performance summary and equity curve
        """
        start_time = time.time()

        # 1. Preload technical indicators
        df_indicators = strategy.preload_indicators(df)
        
        # 2. Generate signals in batch
        df_signals = strategy.generate_signals_batch(df_indicators)

        if 'signal' not in df_signals.columns:
            # Fallback if strategy returns empty signal
            df_signals['signal'] = 'HOLD'

        # 3. Simulate returns vectorially
        close_prices = df_signals['close'].values
        timestamps = df_signals['timestamp'].values
        signals = df_signals['signal'].values
        
        # Convert string signals to position shifts
        # +1 position for BUY, 0 for HOLD/EXIT
        positions = np.zeros(len(signals))
        curr_pos = 0.0
        
        for i in range(len(signals)):
            sig = signals[i]
            if sig == SignalType.BUY.value or sig == SignalType.BUY:
                curr_pos = 1.0
            elif sig == SignalType.SELL.value or sig == SignalType.SELL or sig == SignalType.EXIT.value or sig == SignalType.EXIT:
                curr_pos = 0.0
            positions[i] = curr_pos

        # Shift positions by 1 bar to prevent lookahead bias (execute at next bar open)
        # Position for index i is decided by signal at i-1
        execution_positions = np.roll(positions, 1)
        execution_positions[0] = 0.0

        # Calculate returns
        returns = np.zeros(len(close_prices))
        returns[1:] = np.diff(close_prices) / close_prices[:-1]
        
        # Strategy daily returns = position * daily return
        strategy_returns = execution_positions * returns
        
        # Reconstruct equity curve
        equity_curve = self.initial_capital * np.cumprod(1.0 + strategy_returns)
        
        # Extract trades
        trades = []
        in_trade = False
        entry_price = 0.0
        entry_time = None
        entry_idx = 0
        
        for i in range(len(positions)):
            pos = positions[i]
            price = close_prices[i]
            ts = timestamps[i]
            
            if pos == 1.0 and not in_trade:
                in_trade = True
                entry_price = price
                entry_time = ts
                entry_idx = i
            elif pos == 0.0 and in_trade:
                # Sell/Exit
                in_trade = False
                pnl = (price - entry_price) * (self.initial_capital / entry_price)
                pnl_pct = ((price - entry_price) / entry_price) * 100.0
                trades.append({
                    "symbol": "STOCK",
                    "entry_time": entry_time,
                    "exit_time": ts,
                    "entry_price": entry_price,
                    "exit_price": price,
                    "quantity": int(self.initial_capital / entry_price),
                    "pnl": pnl,
                    "pnl_percent": pnl_pct,
                    "holding_bars": i - entry_idx,
                    "exit_reason": "SIGNAL"
                })
                
        # Close out active trade at last bar close
        if in_trade:
            price = close_prices[-1]
            ts = timestamps[-1]
            pnl = (price - entry_price) * (self.initial_capital / entry_price)
            pnl_pct = ((price - entry_price) / entry_price) * 100.0
            trades.append({
                "symbol": "STOCK",
                "entry_time": entry_time,
                "exit_time": ts,
                "entry_price": entry_price,
                "exit_price": price,
                "quantity": int(self.initial_capital / entry_price),
                "pnl": pnl,
                "pnl_percent": pnl_pct,
                "holding_bars": len(close_prices) - 1 - entry_idx,
                "exit_reason": "FORCE_CLOSE"
            })

        # Calculate metrics using unified calculator
        duration = time.time() - start_time
        ts_list = [str(x) for x in timestamps]
        metrics = UnifiedMetricsCalculator.calculate_performance_summary(
            trades=trades,
            equity_curve=equity_curve.tolist(),
            timestamps=ts_list,
            initial_capital=self.initial_capital
        )
        
        metrics["run_time_seconds"] = round(duration, 4)
        return metrics
