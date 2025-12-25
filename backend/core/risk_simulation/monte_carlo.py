"""
Monte Carlo Risk Simulation
Bootstrap simulation for risk analysis and ruin probability
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class MonteCarloConfig:
    """Configuration for Monte Carlo simulation"""
    n_simulations: int = 10000  # Number of simulation paths
    initial_capital: float = 1000000.0
    
    # Risk thresholds
    ruin_threshold_pct: float = 50.0  # % drawdown considered ruin
    confidence_levels: List[float] = field(default_factory=lambda: [0.95, 0.99])
    
    # Simulation parameters
    bootstrap_block_size: int = 1  # Block bootstrap size (1 = standard bootstrap)
    use_replacement: bool = True


@dataclass
class MonteCarloResult:
    """Results of Monte Carlo simulation"""
    # Core metrics
    ruin_probability: float
    expected_return: float
    median_return: float
    
    # Drawdown analysis
    expected_max_drawdown: float
    worst_case_drawdown: float  # 99th percentile
    var_95: float  # Value at Risk at 95%
    var_99: float  # Value at Risk at 99%
    cvar_95: float  # Conditional VaR at 95%
    
    # Distribution stats
    return_std: float
    skewness: float
    kurtosis: float
    
    # Confidence intervals
    ci_95_lower: float
    ci_95_upper: float
    ci_99_lower: float
    ci_99_upper: float
    
    # Simulation data
    n_simulations: int
    equity_paths: Optional[np.ndarray] = None  # For visualization
    final_returns: Optional[np.ndarray] = None
    max_drawdowns: Optional[np.ndarray] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'ruin_probability': round(self.ruin_probability * 100, 2),
            'expected_return': round(self.expected_return, 2),
            'median_return': round(self.median_return, 2),
            'expected_max_drawdown': round(self.expected_max_drawdown, 2),
            'worst_case_drawdown': round(self.worst_case_drawdown, 2),
            'var_95': round(self.var_95, 2),
            'var_99': round(self.var_99, 2),
            'cvar_95': round(self.cvar_95, 2),
            'return_std': round(self.return_std, 2),
            'skewness': round(self.skewness, 3),
            'kurtosis': round(self.kurtosis, 3),
            'ci_95_lower': round(self.ci_95_lower, 2),
            'ci_95_upper': round(self.ci_95_upper, 2),
            'ci_99_lower': round(self.ci_99_lower, 2),
            'ci_99_upper': round(self.ci_99_upper, 2),
            'n_simulations': self.n_simulations
        }


class MonteCarloSimulator:
    """
    Monte Carlo simulation for trading risk analysis
    
    Uses bootstrap resampling of historical trade returns
    to generate thousands of possible equity paths
    """
    
    def __init__(self, config: Optional[MonteCarloConfig] = None):
        self.config = config or MonteCarloConfig()
    
    def simulate(
        self,
        trade_returns: List[float],
        trade_pnls: Optional[List[float]] = None
    ) -> MonteCarloResult:
        """
        Run Monte Carlo simulation on historical trade returns
        
        Args:
            trade_returns: List of trade returns (as percentages or decimals)
            trade_pnls: Optional list of P&L values (for absolute analysis)
            
        Returns:
            MonteCarloResult with risk metrics
        """
        if len(trade_returns) < 5:
            raise ValueError("Need at least 5 trades for Monte Carlo simulation")
        
        returns = np.array(trade_returns)
        
        # Normalize to decimals if percentages
        if np.mean(np.abs(returns)) > 1:
            returns = returns / 100.0
        
        n_trades = len(returns)
        n_sims = self.config.n_simulations
        initial = self.config.initial_capital
        
        logger.info(f"Running {n_sims} Monte Carlo simulations with {n_trades} trades")
        
        # Generate simulation paths
        equity_paths = np.zeros((n_sims, n_trades + 1))
        equity_paths[:, 0] = initial
        
        for sim in range(n_sims):
            # Bootstrap resample trades
            if self.config.use_replacement:
                sampled_indices = np.random.choice(n_trades, size=n_trades, replace=True)
            else:
                sampled_indices = np.random.permutation(n_trades)
            
            sampled_returns = returns[sampled_indices]
            
            # Build equity curve
            for i, ret in enumerate(sampled_returns):
                equity_paths[sim, i + 1] = equity_paths[sim, i] * (1 + ret)
        
        # Calculate metrics
        final_equities = equity_paths[:, -1]
        final_returns = (final_equities - initial) / initial * 100  # As percentage
        
        # Calculate max drawdowns for each path
        max_drawdowns = np.zeros(n_sims)
        for sim in range(n_sims):
            path = equity_paths[sim]
            peak = np.maximum.accumulate(path)
            drawdowns = (peak - path) / peak * 100
            max_drawdowns[sim] = np.max(drawdowns)
        
        # Ruin probability (drawdown exceeds threshold)
        ruin_count = np.sum(max_drawdowns >= self.config.ruin_threshold_pct)
        ruin_probability = ruin_count / n_sims
        
        # Return statistics
        expected_return = np.mean(final_returns)
        median_return = np.median(final_returns)
        return_std = np.std(final_returns)
        
        # Drawdown statistics
        expected_max_dd = np.mean(max_drawdowns)
        worst_case_dd = np.percentile(max_drawdowns, 99)
        
        # Value at Risk (negative returns - losses)
        var_95 = np.percentile(final_returns, 5)  # 5th percentile for 95% VaR
        var_99 = np.percentile(final_returns, 1)  # 1st percentile for 99% VaR
        
        # Conditional VaR (expected loss beyond VaR)
        losses_beyond_var = final_returns[final_returns <= var_95]
        cvar_95 = np.mean(losses_beyond_var) if len(losses_beyond_var) > 0 else var_95
        
        # Higher moments
        skewness = float(pd.Series(final_returns).skew())
        kurtosis = float(pd.Series(final_returns).kurtosis())
        
        # Confidence intervals
        ci_95_lower = np.percentile(final_returns, 2.5)
        ci_95_upper = np.percentile(final_returns, 97.5)
        ci_99_lower = np.percentile(final_returns, 0.5)
        ci_99_upper = np.percentile(final_returns, 99.5)
        
        # Sample equity paths for visualization (take 100 random paths)
        sample_indices = np.random.choice(n_sims, size=min(100, n_sims), replace=False)
        sample_paths = equity_paths[sample_indices]
        
        return MonteCarloResult(
            ruin_probability=ruin_probability,
            expected_return=expected_return,
            median_return=median_return,
            expected_max_drawdown=expected_max_dd,
            worst_case_drawdown=worst_case_dd,
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            return_std=return_std,
            skewness=skewness,
            kurtosis=kurtosis,
            ci_95_lower=ci_95_lower,
            ci_95_upper=ci_95_upper,
            ci_99_lower=ci_99_lower,
            ci_99_upper=ci_99_upper,
            n_simulations=n_sims,
            equity_paths=sample_paths,
            final_returns=final_returns,
            max_drawdowns=max_drawdowns
        )
    
    def simulate_from_backtest(
        self,
        backtest_result: Any  # BacktestResult
    ) -> MonteCarloResult:
        """
        Run Monte Carlo simulation using trades from a backtest
        """
        if not hasattr(backtest_result, 'trades') or len(backtest_result.trades) == 0:
            raise ValueError("Backtest result has no trades")
        
        # Extract trade returns
        trade_returns = [t.return_pct for t in backtest_result.trades]
        trade_pnls = [t.net_pnl for t in backtest_result.trades]
        
        return self.simulate(trade_returns, trade_pnls)
    
    def get_fan_chart_data(self, result: MonteCarloResult) -> Dict[str, Any]:
        """
        Get data for fan chart visualization
        
        Returns percentile bands at each time step
        """
        if result.equity_paths is None:
            return {}
        
        paths = result.equity_paths
        n_steps = paths.shape[1]
        
        percentiles = [5, 10, 25, 50, 75, 90, 95]
        bands = {f'p{p}': [] for p in percentiles}
        
        for step in range(n_steps):
            step_values = paths[:, step]
            for p in percentiles:
                bands[f'p{p}'].append(float(np.percentile(step_values, p)))
        
        return {
            'bands': bands,
            'n_steps': n_steps,
            'percentiles': percentiles
        }
