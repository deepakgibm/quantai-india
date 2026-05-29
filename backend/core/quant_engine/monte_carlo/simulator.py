"""
Monte Carlo Simulation Engine
Simulates randomized trading equity curves to evaluate capital risk of ruin.
"""

import numpy as np
from typing import List, Dict, Any


class MonteCarloSimulator:
    """
    Simulates equity curves based on bootstrapping trade results.
    Identifies capital preservation viability.
    """

    def __init__(self, initial_capital: float = 1000000.0):
        self.initial_capital = initial_capital

    def simulate(
        self,
        trade_returns_pct: List[float],
        num_simulations: int = 1000,
        num_trades_per_path: int = 50,
        risk_of_ruin_pct: float = 50.0
    ) -> Dict[str, Any]:
        """
        Runs Monte Carlo simulations on trade logs.
        
        Args:
            trade_returns_pct: List of percentage gains/losses per trade (e.g. [2.5, -1.2, 5.0])
            num_simulations: Number of paths to simulate
            num_trades_per_path: Number of trades per simulated path
            risk_of_ruin_pct: Loss threshold percentage considered 'ruined' (e.g. 50%)
            
        Returns:
            Dict containing percentiles, paths, and risk of ruin probability
        """
        # Fallback if no trades are provided
        if not trade_returns_pct:
            trade_returns_pct = [0.0]

        returns_arr = np.array(trade_returns_pct) / 100.0  # Convert to decimals

        # Matrix of random selections (with replacement)
        # Dimensions: num_simulations x num_trades_per_path
        random_indices = np.random.choice(
            len(returns_arr),
            size=(num_simulations, num_trades_per_path),
            replace=True
        )
        sampled_returns = returns_arr[random_indices]

        # Calculate equity curve paths starting at initial capital
        # Cumulative product along columns
        growth_factors = np.cumprod(1.0 + sampled_returns, axis=1)
        paths = self.initial_capital * growth_factors
        # Prepend initial capital to the start of each path
        paths = np.hstack((np.full((num_simulations, 1), self.initial_capital), paths))

        # Calculate drawdowns per path
        peaks = np.maximum.accumulate(paths, axis=1)
        drawdowns = (paths - peaks) / peaks
        max_drawdowns = np.min(drawdowns, axis=1) * 100.0  # convert to percentage losses

        # Percentile boundaries
        median_curve = np.percentile(paths, 50, axis=0)
        upper_95_curve = np.percentile(paths, 95, axis=0)
        lower_5_curve = np.percentile(paths, 5, axis=0)

        # Risk of ruin: fraction of simulations where capital drops below ruin threshold
        ruin_level = self.initial_capital * (1.0 - (risk_of_ruin_pct / 100.0))
        min_equity_per_path = np.min(paths, axis=1)
        ruin_count = np.sum(min_equity_per_path <= ruin_level)
        prob_of_ruin = (ruin_count / num_simulations) * 100.0

        # Sample a subset of actual paths (e.g., 20 paths) to display on charts
        sample_paths = paths[:30].tolist()

        return {
            "num_simulations": num_simulations,
            "risk_of_ruin_probability": round(prob_of_ruin, 2),
            "median_equity": median_curve.tolist(),
            "upper_95_percentile": upper_95_curve.tolist(),
            "lower_5_percentile": lower_5_curve.tolist(),
            "sample_paths": sample_paths,
            "worst_case_drawdown": round(float(np.min(max_drawdowns)), 2),
            "average_max_drawdown": round(float(np.mean(max_drawdowns)), 2),
            "median_final_equity": round(float(np.median(paths[:, -1])), 2)
        }
