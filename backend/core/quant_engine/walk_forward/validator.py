"""
Walk-Forward Engine
Implements In-Sample / Out-of-Sample rolling validation protocols.
"""

import pandas as pd
from typing import List, Dict, Any, Type

from ..strategy.base import UnifiedStrategy
from ..execution.vectorized import VectorizedExecutionEngine
from ..metrics.calculator import UnifiedMetricsCalculator


class WalkForwardValidator:
    """
    Pardo-compliant Walk-Forward In-Sample & Out-of-Sample Validation Engine.
    Standardizes rolling-window param optimization.
    """

    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.runner = VectorizedExecutionEngine(initial_capital)

    def generate_windows(
        self,
        df: pd.DataFrame,
        train_window_bars: int,
        test_window_bars: int,
        step_bars: int,
        anchored: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Partition raw dataframe into chronological rolling train/test bar boundaries.
        """
        windows = []
        n_bars = len(df)
        
        current_idx = 0
        window_id = 0
        
        while current_idx + train_window_bars + test_window_bars <= n_bars:
            train_start = 0 if anchored else current_idx
            train_end = train_start + train_window_bars + (current_idx if anchored else 0) - 1
            
            test_start = train_end + 1
            test_end = test_start + test_window_bars - 1
            
            if test_end >= n_bars:
                break
                
            windows.append({
                "window_id": window_id,
                "train_start_idx": train_start,
                "train_end_idx": train_end,
                "test_start_idx": test_start,
                "test_end_idx": test_end,
                "train_dates": (df['timestamp'].iloc[train_start], df['timestamp'].iloc[train_end]),
                "test_dates": (df['timestamp'].iloc[test_start], df['timestamp'].iloc[test_end])
            })
            
            window_id += 1
            current_idx += step_bars
            
        return windows

    def run_walk_forward(
        self,
        strategy_class: Type[UnifiedStrategy],
        df: pd.DataFrame,
        param_grid: List[Dict[str, Any]],
        train_window_bars: int,
        test_window_bars: int,
        step_bars: int,
        anchored: bool = False
    ) -> Dict[str, Any]:
        """
        Runs the complete walk-forward validation process:
        1. Splitting windows
        2. Optimization on In-Sample (IS) per window
        3. Backtesting best parameters on Out-of-Sample (OOS)
        4. Stitching OOS equity curve
        """
        windows = self.generate_windows(
            df=df,
            train_window_bars=train_window_bars,
            test_window_bars=test_window_bars,
            step_bars=step_bars,
            anchored=anchored
        )

        if len(windows) < 1:
            raise ValueError("Dataframe length is too short to generate rolling validation windows.")

        window_results = []
        oos_equity_curve = [self.initial_capital]
        oos_trades = []
        current_oos_capital = self.initial_capital

        for win in windows:
            # Slices data
            train_df = df.iloc[win["train_start_idx"]:win["train_end_idx"]+1].reset_index(drop=True)
            test_df = df.iloc[win["test_start_idx"]:win["test_end_idx"]+1].reset_index(drop=True)

            # A. OPTIMIZE: Run parameter sweep on In-Sample (IS) data
            best_params = None
            best_is_metric = -99999.0
            
            # Simple grid search optimizer over parameters
            for params in param_grid:
                strat_inst = strategy_class(params)
                is_res = self.runner.run(strat_inst, train_df)
                # Optimize for Sharpe Ratio
                is_metric = is_res.get("sharpe_ratio", 0.0)
                if is_metric > best_is_metric:
                    best_is_metric = is_metric
                    best_params = params

            if not best_params:
                best_params = param_grid[0]

            # B. BACKTEST OOS: Run on Out-of-Sample (OOS) data with frozen best params
            test_runner = VectorizedExecutionEngine(current_oos_capital)
            strat_inst_oos = strategy_class(best_params)
            oos_res = test_runner.run(strat_inst_oos, test_df)

            # C. Record window results
            win_pnl = oos_res.get("total_pnl", 0.0)
            current_oos_capital += win_pnl

            # Offset the equity curve to stitch properly
            win_equity = oos_res.get("equity_curve", [current_oos_capital])
            if len(oos_equity_curve) > 1 and win_equity:
                # Adjust equity values relative to prior capital
                start_val = oos_equity_curve[-1]
                ratio = start_val / win_equity[0] if win_equity[0] > 0 else 1.0
                adjusted_curve = [x * ratio for x in win_equity]
                oos_equity_curve.extend(adjusted_curve[1:])
            else:
                oos_equity_curve.extend(win_equity)

            # Record trades
            # Standardize trades with adjusted pnl
            window_results.append({
                "window_id": win["window_id"],
                "train_start": str(win["train_dates"][0]),
                "train_end": str(win["train_dates"][1]),
                "test_start": str(win["test_dates"][0]),
                "test_end": str(win["test_dates"][1]),
                "is_sharpe": best_is_metric,
                "oos_return": oos_res.get("total_return_pct", 0.0),
                "oos_sharpe": oos_res.get("sharpe_ratio", 0.0),
                "oos_drawdown": oos_res.get("max_drawdown_pct", 0.0),
                "oos_trades": oos_res.get("total_trades", 0),
                "best_parameters": best_params
            })

        # Calculate stitched summary metrics
        timestamps = [str(x) for x in df['timestamp'].values[windows[0]["test_start_idx"]:]]
        # Align equity curve length with timestamps
        if len(oos_equity_curve) > len(timestamps):
            oos_equity_curve = oos_equity_curve[-len(timestamps):]
        elif len(oos_equity_curve) < len(timestamps):
            timestamps = timestamps[-len(oos_equity_curve):]

        summary = UnifiedMetricsCalculator.calculate_performance_summary(
            trades=[],
            equity_curve=oos_equity_curve,
            timestamps=timestamps,
            initial_capital=self.initial_capital
        )

        # Validate parameters stability
        param_changes = 0
        if len(window_results) > 1:
            for idx in range(1, len(window_results)):
                if window_results[idx]["best_parameters"] != window_results[idx-1]["best_parameters"]:
                    param_changes += 1
            stability = 1.0 - (param_changes / (len(window_results) - 1))
        else:
            stability = 1.0

        # Auto check pass/fail
        profitable_windows = sum(1 for w in window_results if w["oos_return"] > 0)
        profitable_pct = (profitable_windows / len(window_results) * 100.0) if window_results else 0.0
        
        validation_passed = (profitable_pct >= 60.0) and (stability >= 0.3)
        validation_messages = []
        
        if profitable_pct < 60.0:
            validation_messages.append(f"OOS profitable windows count is {profitable_pct:.1f}% (required >= 60%)")
        else:
            validation_messages.append(f"OOS profitable windows check passed: {profitable_pct:.1f}%")
            
        if stability < 0.3:
            validation_messages.append(f"High parameter instability detected. Stability score: {stability:.2f}")
        else:
            validation_messages.append(f"Parameter stability check passed: {stability:.2f}")

        return {
            "summary": {
                "total_return": summary["total_return_pct"],
                "sharpe": summary["sharpe_ratio"],
                "max_drawdown": summary["max_drawdown_pct"],
                "profitable_windows_pct": profitable_pct,
                "parameter_stability_score": stability
            },
            "validation_passed": validation_passed,
            "validation_messages": validation_messages,
            "window_results": window_results,
            "equity_curve": [{"date": t, "equity": eq} for t, eq in zip(timestamps, oos_equity_curve)]
        }
