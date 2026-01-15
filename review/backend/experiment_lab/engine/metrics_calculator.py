"""
Metrics Calculator for Experiment Lab
Calculates comprehensive performance metrics from backtest results.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TradeRecord:
    """Record of a single trade."""
    entry_time: datetime
    exit_time: datetime
    signal_type: str  # BUY or SELL
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    pnl_percent: float
    holding_bars: int
    exit_reason: str  # TARGET, STOP, SIGNAL, MAX_HOLD


@dataclass 
class BacktestMetrics:
    """Complete backtest performance metrics."""
    # Basic Metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # Returns
    total_pnl: float = 0.0
    total_return_pct: float = 0.0
    cagr: float = 0.0
    
    # Risk Metrics
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Trade Analysis
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_holding_period: float = 0.0
    
    # Capital
    initial_capital: float = 0.0
    final_capital: float = 0.0
    
    # Equity curve data
    equity_curve: List[float] = field(default_factory=list)
    drawdown_curve: List[float] = field(default_factory=list)
    
    # Trade log
    trades: List[TradeRecord] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(self.win_rate, 2),
            "total_pnl": round(self.total_pnl, 2),
            "total_return_pct": round(self.total_return_pct, 2),
            "cagr": round(self.cagr, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "sortino_ratio": round(self.sortino_ratio, 2),
            "calmar_ratio": round(self.calmar_ratio, 2),
            "profit_factor": round(self.profit_factor, 2),
            "avg_win": round(self.avg_win, 2),
            "avg_loss": round(self.avg_loss, 2),
            "avg_win_pct": round(self.avg_win_pct, 2),
            "avg_loss_pct": round(self.avg_loss_pct, 2),
            "largest_win": round(self.largest_win, 2),
            "largest_loss": round(self.largest_loss, 2),
            "avg_holding_period": round(self.avg_holding_period, 1),
            "initial_capital": round(self.initial_capital, 2),
            "final_capital": round(self.final_capital, 2),
            "equity_curve": [round(x, 2) for x in self.equity_curve[-100:]],  # Last 100 points
            "drawdown_curve": [round(x, 2) for x in self.drawdown_curve[-100:]],
        }


class MetricsCalculator:
    """
    Calculates comprehensive performance metrics from trade results.
    """
    
    def __init__(self, initial_capital: float = 1000000, risk_free_rate: float = 0.05):
        self.initial_capital = initial_capital
        self.risk_free_rate = risk_free_rate  # Annual risk-free rate
    
    def calculate(
        self,
        trades: List[TradeRecord],
        equity_curve: Optional[List[float]] = None,
        trading_days: int = 252
    ) -> BacktestMetrics:
        """
        Calculate all performance metrics from trade records.
        
        Args:
            trades: List of TradeRecord objects
            equity_curve: Optional equity curve (if pre-calculated)
            trading_days: Number of trading days per year
            
        Returns:
            BacktestMetrics with all calculated metrics
        """
        metrics = BacktestMetrics(
            initial_capital=self.initial_capital,
            trades=trades
        )
        
        if not trades:
            metrics.final_capital = self.initial_capital
            return metrics
        
        # Basic counts
        metrics.total_trades = len(trades)
        metrics.winning_trades = sum(1 for t in trades if t.pnl > 0)
        metrics.losing_trades = sum(1 for t in trades if t.pnl <= 0)
        metrics.win_rate = (metrics.winning_trades / metrics.total_trades * 100) if metrics.total_trades > 0 else 0
        
        # PnL calculations
        pnls = [t.pnl for t in trades]
        pnl_pcts = [t.pnl_percent for t in trades]
        
        metrics.total_pnl = sum(pnls)
        metrics.final_capital = self.initial_capital + metrics.total_pnl
        metrics.total_return_pct = (metrics.total_pnl / self.initial_capital) * 100
        
        # Win/Loss analysis
        wins = [t.pnl for t in trades if t.pnl > 0]
        losses = [abs(t.pnl) for t in trades if t.pnl <= 0]
        win_pcts = [t.pnl_percent for t in trades if t.pnl > 0]
        loss_pcts = [abs(t.pnl_percent) for t in trades if t.pnl <= 0]
        
        metrics.avg_win = np.mean(wins) if wins else 0
        metrics.avg_loss = np.mean(losses) if losses else 0
        metrics.avg_win_pct = np.mean(win_pcts) if win_pcts else 0
        metrics.avg_loss_pct = np.mean(loss_pcts) if loss_pcts else 0
        metrics.largest_win = max(pnls) if pnls else 0
        metrics.largest_loss = min(pnls) if pnls else 0
        
        # Profit Factor
        gross_profit = sum(wins) if wins else 0
        gross_loss = sum(losses) if losses else 1
        metrics.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Holding period
        holding_periods = [t.holding_bars for t in trades]
        metrics.avg_holding_period = np.mean(holding_periods) if holding_periods else 0
        
        # Calculate equity curve if not provided
        if equity_curve is None:
            equity_curve = [self.initial_capital]
            running_capital = self.initial_capital
            for t in trades:
                running_capital += t.pnl
                equity_curve.append(running_capital)
        
        metrics.equity_curve = equity_curve
        
        # Drawdown calculation
        if equity_curve:
            equity_array = np.array(equity_curve)
            running_max = np.maximum.accumulate(equity_array)
            drawdown = running_max - equity_array
            drawdown_pct = (drawdown / running_max) * 100
            
            metrics.max_drawdown = float(np.max(drawdown))
            metrics.max_drawdown_pct = float(np.max(drawdown_pct))
            metrics.drawdown_curve = drawdown_pct.tolist()
        
        # CAGR calculation
        if len(trades) > 0:
            first_trade = trades[0].entry_time
            last_trade = trades[-1].exit_time
            if hasattr(first_trade, 'timestamp'):
                first_trade = first_trade
            if hasattr(last_trade, 'timestamp'):
                last_trade = last_trade
            
            try:
                years = (last_trade - first_trade).days / 365.25 if hasattr(last_trade, '__sub__') else 1
                if years > 0 and metrics.final_capital > 0 and self.initial_capital > 0:
                    metrics.cagr = ((metrics.final_capital / self.initial_capital) ** (1 / years) - 1) * 100
            except:
                metrics.cagr = metrics.total_return_pct
        
        # Risk-adjusted metrics
        if pnl_pcts and len(pnl_pcts) > 1:
            returns_std = np.std(pnl_pcts)
            if returns_std > 0:
                mean_return = np.mean(pnl_pcts)
                # Annualize
                annualized_return = mean_return * trading_days
                annualized_std = returns_std * np.sqrt(trading_days)
                
                # Sharpe Ratio
                metrics.sharpe_ratio = (annualized_return - self.risk_free_rate) / annualized_std if annualized_std > 0 else 0
                
                # Sortino Ratio (downside deviation)
                downside_returns = [r for r in pnl_pcts if r < 0]
                if downside_returns:
                    downside_std = np.std(downside_returns) * np.sqrt(trading_days)
                    metrics.sortino_ratio = (annualized_return - self.risk_free_rate) / downside_std if downside_std > 0 else 0
                
                # Calmar Ratio
                if metrics.max_drawdown_pct > 0:
                    metrics.calmar_ratio = metrics.cagr / metrics.max_drawdown_pct
        
        return metrics
    
    def compare_strategies(self, results: Dict[int, BacktestMetrics]) -> List[Dict]:
        """
        Compare multiple strategy results and rank them.
        
        Args:
            results: Dictionary mapping strategy_id to BacktestMetrics
            
        Returns:
            List of rankings by different criteria
        """
        if not results:
            return []
        
        rankings = []
        
        # Rank by Return
        by_return = sorted(results.items(), key=lambda x: x[1].total_return_pct, reverse=True)
        rankings.append({
            "criterion": "Highest Return",
            "ranking": [{"strategy_id": sid, "value": m.total_return_pct} for sid, m in by_return[:10]]
        })
        
        # Rank by Drawdown (lower is better)
        by_drawdown = sorted(results.items(), key=lambda x: x[1].max_drawdown_pct)
        rankings.append({
            "criterion": "Lowest Drawdown",
            "ranking": [{"strategy_id": sid, "value": m.max_drawdown_pct} for sid, m in by_drawdown[:10]]
        })
        
        # Rank by Risk-Adjusted Return (Sharpe)
        by_sharpe = sorted(results.items(), key=lambda x: x[1].sharpe_ratio, reverse=True)
        rankings.append({
            "criterion": "Best Risk-Adjusted (Sharpe)",
            "ranking": [{"strategy_id": sid, "value": m.sharpe_ratio} for sid, m in by_sharpe[:10]]
        })
        
        # Rank by Win Rate
        by_winrate = sorted(results.items(), key=lambda x: x[1].win_rate, reverse=True)
        rankings.append({
            "criterion": "Highest Win Rate",
            "ranking": [{"strategy_id": sid, "value": m.win_rate} for sid, m in by_winrate[:10]]
        })
        
        return rankings


__all__ = ['TradeRecord', 'BacktestMetrics', 'MetricsCalculator']
