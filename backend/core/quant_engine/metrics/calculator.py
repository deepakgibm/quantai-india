"""
Unified Metrics Engine
Standardized quantitative metric calculations for Sharpe, Sortino, CAGR, Drawdown, Calmar, and Expectancy.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple


class UnifiedMetricsCalculator:
    """
    Unified metrics calculation engine.
    Applies consistent mathematical formulas across all simulation runtimes.
    """

    @staticmethod
    def calculate_drawdown(equity_curve: np.ndarray) -> Tuple[float, np.ndarray]:
        """
        Calculate maximum drawdown and drawdown curve.
        """
        if len(equity_curve) == 0:
            return 0.0, np.array([0.0])
        
        peak = np.maximum.accumulate(equity_curve)
        # Avoid division by zero
        drawdowns = np.where(peak > 0, (equity_curve - peak) / peak, 0.0)
        max_dd = abs(np.min(drawdowns)) * 100.0
        return max_dd, drawdowns * 100.0

    @staticmethod
    def calculate_cagr(initial_capital: float, final_equity: float, start_date: Any, end_date: Any) -> float:
        """
        Calculate Compound Annual Growth Rate (CAGR).
        """
        if initial_capital <= 0 or final_equity <= 0:
            return 0.0
            
        try:
            days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
            if days <= 0:
                return 0.0
            years = days / 365.25
            cagr = ((final_equity / initial_capital) ** (1.0 / years) - 1.0) * 100.0
            return cagr
        except Exception:
            return 0.0

    @staticmethod
    def calculate_sharpe(returns: np.ndarray, risk_free_rate: float = 0.05, periods_per_year: int = 252) -> float:
        """
        Calculate annualized Sharpe Ratio.
        """
        if len(returns) < 2 or np.std(returns) == 0:
            return 0.0
            
        mean_ret = np.mean(returns) * periods_per_year
        std_ret = np.std(returns) * np.sqrt(periods_per_year)
        
        return (mean_ret - risk_free_rate) / std_ret if std_ret > 0 else 0.0

    @staticmethod
    def calculate_sortino(returns: np.ndarray, risk_free_rate: float = 0.05, periods_per_year: int = 252) -> float:
        """
        Calculate annualized Sortino Ratio (only downside returns volatility).
        """
        if len(returns) < 2:
            return 0.0
            
        downside_returns = returns[returns < 0]
        if len(downside_returns) < 2:
            # No downside risk
            return 9.99
            
        mean_ret = np.mean(returns) * periods_per_year
        downside_std = np.std(downside_returns) * np.sqrt(periods_per_year)
        
        return (mean_ret - risk_free_rate) / downside_std if downside_std > 0 else 0.0

    @staticmethod
    def calculate_cvar(returns: np.ndarray, confidence: float = 0.95) -> float:
        """
        Calculate Conditional Value at Risk (Expected Shortfall).
        """
        if len(returns) == 0:
            return 0.0
        var = np.percentile(returns, (1 - confidence) * 100)
        tail_losses = returns[returns <= var]
        if len(tail_losses) == 0:
            return abs(var)
        return abs(np.mean(tail_losses))

    @classmethod
    def calculate_performance_summary(
        cls,
        trades: List[Dict[str, Any]],
        equity_curve: List[float],
        timestamps: List[Any],
        initial_capital: float
    ) -> Dict[str, Any]:
        """
        Compute standard quant statistics from trades and equity timeline.
        """
        equity_arr = np.array(equity_curve)
        final_equity = equity_arr[-1] if len(equity_arr) > 0 else initial_capital
        total_pnl = final_equity - initial_capital
        total_return_pct = (total_pnl / initial_capital) * 100.0

        # Drawdowns
        max_dd, dd_curve = cls.calculate_drawdown(equity_arr)

        # CAGR
        start_date = timestamps[0] if timestamps else None
        end_date = timestamps[-1] if timestamps else None
        cagr = cls.calculate_cagr(initial_capital, final_equity, start_date, end_date)

        # Returns metrics
        returns = np.diff(equity_arr) / equity_arr[:-1] if len(equity_arr) > 1 else np.array([0.0])
        sharpe = cls.calculate_sharpe(returns)
        sortino = cls.calculate_sortino(returns)
        
        calmar = cagr / max_dd if max_dd > 0 else 0.0

        # Trades metrics
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.get("pnl", 0) > 0)
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0

        wins = [t.get("pnl", 0) for t in trades if t.get("pnl", 0) > 0]
        losses = [abs(t.get("pnl", 0)) for t in trades if t.get("pnl", 0) <= 0]

        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = np.mean(losses) if losses else 0.0

        gross_profit = sum(wins)
        gross_loss = sum(losses)
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

        # Expectancy: (Win Rate * Avg Win) - (Loss Rate * Avg Loss)
        win_rate_ratio = win_rate / 100.0
        expectancy = (win_rate_ratio * avg_win) - ((1 - win_rate_ratio) * avg_loss)

        avg_holding = np.mean([t.get("holding_bars", 0) for t in trades]) if total_trades > 0 else 0.0

        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "total_return_pct": round(total_return_pct, 2),
            "cagr": round(cagr, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "sharpe_ratio": round(sharpe, 3),
            "sortino_ratio": round(sortino, 3),
            "calmar_ratio": round(calmar, 3),
            "profit_factor": round(profit_factor, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "expectancy": round(expectancy, 2),
            "avg_holding_period": round(avg_holding, 1),
            "initial_capital": round(initial_capital, 2),
            "final_capital": round(final_equity, 2),
            "equity_curve": equity_curve,
            "drawdown_curve": dd_curve.tolist(),
            "trades": trades
        }
