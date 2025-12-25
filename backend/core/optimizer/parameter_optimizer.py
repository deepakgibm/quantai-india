"""
Parameter Optimizer
Grid search, random search, and Bayesian optimization for strategy parameters
"""

from typing import Dict, List, Any, Optional, Callable, Type
from dataclasses import dataclass, field
from datetime import date
from itertools import product
import numpy as np
import pandas as pd
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
import json

from ..backtest.engine import BacktestEngine, BacktestConfig, BacktestResult
from ..strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


@dataclass
class OptimizationConstraints:
    """Guardrails for optimization"""
    max_drawdown_pct: float = 25.0  # Maximum allowed drawdown
    min_sharpe: float = 0.5  # Minimum Sharpe ratio
    min_win_rate: float = 35.0  # Minimum win rate %
    min_profit_factor: float = 1.0  # Minimum profit factor
    min_trades: int = 10  # Minimum number of trades
    min_rr_ratio: float = 1.5  # Minimum risk:reward ratio


@dataclass
class OptimizationConfig:
    """Configuration for parameter optimization"""
    symbol: str
    start_date: date
    end_date: date
    initial_capital: float = 1000000.0
    
    # Search method
    method: str = "grid"  # grid, random, bayesian
    
    # For random search
    n_iterations: int = 100
    
    # Constraints
    constraints: OptimizationConstraints = field(default_factory=OptimizationConstraints)
    
    # Parallel execution
    n_jobs: int = 1  # Number of parallel workers
    
    # Objective function
    objective: str = "sharpe"  # sharpe, return, calmar, sortino


@dataclass
class OptimizationResult:
    """Result of a single optimization run"""
    params: Dict[str, Any]
    metrics: Dict[str, float]
    passed_constraints: bool
    objective_value: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'params': self.params,
            'metrics': self.metrics,
            'passed_constraints': self.passed_constraints,
            'objective_value': round(self.objective_value, 4)
        }


@dataclass
class OptimizationSummary:
    """Summary of optimization run"""
    best_params: Dict[str, Any]
    best_metrics: Dict[str, float]
    best_objective: float
    
    total_combinations: int
    valid_combinations: int
    failed_combinations: int
    
    all_results: List[OptimizationResult]
    
    method: str
    elapsed_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'best_params': self.best_params,
            'best_metrics': self.best_metrics,
            'best_objective': round(self.best_objective, 4),
            'total_combinations': self.total_combinations,
            'valid_combinations': self.valid_combinations,
            'failed_combinations': self.failed_combinations,
            'method': self.method,
            'elapsed_seconds': round(self.elapsed_seconds, 2),
            'top_5': [r.to_dict() for r in sorted(
                [r for r in self.all_results if r.passed_constraints],
                key=lambda x: x.objective_value,
                reverse=True
            )[:5]]
        }


class ParameterOptimizer:
    """
    Parameter optimization engine with guardrails
    
    Supports:
    - Grid search: Exhaustive search over parameter grid
    - Random search: Random sampling from parameter space
    - Bayesian optimization: Using Gaussian processes (optional)
    """
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self._data: Optional[pd.DataFrame] = None
    
    def set_data(self, data: pd.DataFrame) -> None:
        """Set the data to use for optimization"""
        self._data = data
    
    def optimize(
        self,
        strategy_class: Type[BaseStrategy],
        param_grid: Dict[str, List[Any]]
    ) -> OptimizationSummary:
        """
        Run parameter optimization
        
        Args:
            strategy_class: Strategy class to optimize
            param_grid: Dictionary of parameter names to lists of values
            
        Returns:
            OptimizationSummary with best parameters and all results
        """
        import time
        start_time = time.time()
        
        if self._data is None:
            raise ValueError("No data set. Call set_data() first.")
        
        # Generate parameter combinations
        if self.config.method == "grid":
            param_combos = self._generate_grid_combinations(param_grid)
        elif self.config.method == "random":
            param_combos = self._generate_random_combinations(param_grid)
        elif self.config.method == "bayesian":
            return self._bayesian_optimize(strategy_class, param_grid, start_time)
        else:
            raise ValueError(f"Unknown optimization method: {self.config.method}")
        
        logger.info(f"Running {self.config.method} optimization with {len(param_combos)} combinations")
        
        results: List[OptimizationResult] = []
        failed = 0
        
        for i, params in enumerate(param_combos):
            try:
                result = self._evaluate_params(strategy_class, params)
                results.append(result)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Progress: {i + 1}/{len(param_combos)}")
                    
            except Exception as e:
                logger.warning(f"Failed to evaluate params {params}: {e}")
                failed += 1
                continue
        
        # Find best result
        valid_results = [r for r in results if r.passed_constraints]
        
        if valid_results:
            best = max(valid_results, key=lambda x: x.objective_value)
            best_params = best.params
            best_metrics = best.metrics
            best_objective = best.objective_value
        else:
            # No valid results, take best from all
            if results:
                best = max(results, key=lambda x: x.objective_value)
                best_params = best.params
                best_metrics = best.metrics
                best_objective = best.objective_value
            else:
                best_params = {}
                best_metrics = {}
                best_objective = float('-inf')
        
        elapsed = time.time() - start_time
        
        return OptimizationSummary(
            best_params=best_params,
            best_metrics=best_metrics,
            best_objective=best_objective,
            total_combinations=len(param_combos),
            valid_combinations=len(valid_results),
            failed_combinations=failed,
            all_results=results,
            method=self.config.method,
            elapsed_seconds=elapsed
        )
    
    def _bayesian_optimize(
        self,
        strategy_class: Type[BaseStrategy],
        param_grid: Dict[str, List[Any]],
        start_time: float
    ) -> OptimizationSummary:
        """
        Bayesian optimization using Gaussian Process surrogate
        
        Uses Upper Confidence Bound (UCB) acquisition function
        """
        import time
        from scipy.stats import norm
        from scipy.optimize import minimize
        
        logger.info(f"Running Bayesian optimization for {self.config.n_iterations} iterations")
        
        # Convert param grid to bounds
        param_names = list(param_grid.keys())
        param_values = [param_grid[k] for k in param_names]
        param_indices = {k: list(range(len(v))) for k, v in param_grid.items()}
        
        # Initialize with random samples
        n_init = min(10, self.config.n_iterations // 3)
        
        X_observed = []  # Parameter indices
        y_observed = []  # Objective values
        results: List[OptimizationResult] = []
        failed = 0
        
        # Initial random exploration
        for i in range(n_init):
            params = {k: np.random.choice(v) for k, v in param_grid.items()}
            x = [param_grid[k].index(params[k]) for k in param_names]
            
            try:
                result = self._evaluate_params(strategy_class, params)
                results.append(result)
                X_observed.append(x)
                y_observed.append(result.objective_value)
            except Exception as e:
                logger.warning(f"Init {i} failed: {e}")
                failed += 1
        
        # Bayesian optimization loop
        for i in range(n_init, self.config.n_iterations):
            if len(X_observed) < 2:
                # Not enough data, random sample
                params = {k: np.random.choice(v) for k, v in param_grid.items()}
            else:
                # Fit simple GP-like model (using weighted average as surrogate)
                X = np.array(X_observed)
                y = np.array(y_observed)
                
                # Find next point using UCB acquisition
                best_acq = float('-inf')
                best_params = None
                
                # Sample candidates
                n_candidates = 100
                for _ in range(n_candidates):
                    candidate = {k: np.random.choice(v) for k, v in param_grid.items()}
                    x_cand = np.array([param_grid[k].index(candidate[k]) for k in param_names])
                    
                    # Simple distance-weighted prediction (GP approximation)
                    distances = np.sqrt(np.sum((X - x_cand) ** 2, axis=1) + 1e-6)
                    weights = 1.0 / distances
                    weights /= weights.sum()
                    
                    # Mean prediction
                    mu = np.sum(weights * y)
                    
                    # Uncertainty (inverse of similarity)
                    sigma = np.sqrt(np.sum(weights * (y - mu) ** 2)) + 0.1
                    
                    # UCB acquisition: mu + kappa * sigma
                    kappa = 2.0  # Exploration-exploitation trade-off
                    acq = mu + kappa * sigma
                    
                    if acq > best_acq:
                        best_acq = acq
                        best_params = candidate
                
                params = best_params if best_params else {k: np.random.choice(v) for k, v in param_grid.items()}
            
            x = [param_grid[k].index(params[k]) for k in param_names]
            
            try:
                result = self._evaluate_params(strategy_class, params)
                results.append(result)
                X_observed.append(x)
                y_observed.append(result.objective_value)
                
                if (i + 1) % 10 == 0:
                    best_so_far = max(y_observed)
                    logger.info(f"Bayesian iter {i + 1}/{self.config.n_iterations}, best={best_so_far:.4f}")
                    
            except Exception as e:
                logger.warning(f"Bayesian iter {i} failed: {e}")
                failed += 1
        
        # Find best result
        valid_results = [r for r in results if r.passed_constraints]
        
        if valid_results:
            best = max(valid_results, key=lambda x: x.objective_value)
        elif results:
            best = max(results, key=lambda x: x.objective_value)
        else:
            best = None
        
        elapsed = time.time() - start_time
        
        return OptimizationSummary(
            best_params=best.params if best else {},
            best_metrics=best.metrics if best else {},
            best_objective=best.objective_value if best else float('-inf'),
            total_combinations=len(results) + failed,
            valid_combinations=len(valid_results),
            failed_combinations=failed,
            all_results=results,
            method="bayesian",
            elapsed_seconds=elapsed
        )
    
    def _generate_grid_combinations(
        self,
        param_grid: Dict[str, List[Any]]
    ) -> List[Dict[str, Any]]:
        """Generate all combinations for grid search"""
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        
        combinations = []
        for combo in product(*values):
            combinations.append(dict(zip(keys, combo)))
        
        return combinations
    
    def _generate_random_combinations(
        self,
        param_grid: Dict[str, List[Any]]
    ) -> List[Dict[str, Any]]:
        """Generate random combinations for random search"""
        combinations = []
        
        for _ in range(self.config.n_iterations):
            params = {}
            for key, values in param_grid.items():
                params[key] = np.random.choice(values)
            combinations.append(params)
        
        return combinations
    
    def _evaluate_params(
        self,
        strategy_class: Type[BaseStrategy],
        params: Dict[str, Any]
    ) -> OptimizationResult:
        """Evaluate a single parameter combination"""
        # Create backtest config
        bt_config = BacktestConfig(
            symbol=self.config.symbol,
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            initial_capital=self.config.initial_capital
        )
        
        # Run backtest
        engine = BacktestEngine(bt_config)
        engine.load_data(self._data)
        
        strategy = strategy_class(params)
        result = engine.run(strategy)
        
        # Extract metrics
        metrics = {
            'total_return_pct': result.metrics.total_return_pct,
            'sharpe_ratio': result.metrics.sharpe_ratio,
            'sortino_ratio': result.metrics.sortino_ratio,
            'max_drawdown_pct': result.metrics.max_drawdown_pct,
            'win_rate': result.metrics.win_rate,
            'profit_factor': result.metrics.profit_factor,
            'total_trades': result.metrics.total_trades,
            'calmar_ratio': result.metrics.calmar_ratio,
            'cagr': result.metrics.cagr,
            'avg_win': result.metrics.avg_win,
            'avg_loss': result.metrics.avg_loss
        }
        
        # Check constraints
        passed = self._check_constraints(metrics)
        
        # Calculate objective
        objective = self._calculate_objective(metrics)
        
        return OptimizationResult(
            params=params,
            metrics=metrics,
            passed_constraints=passed,
            objective_value=objective
        )
    
    def _check_constraints(self, metrics: Dict[str, float]) -> bool:
        """Check if metrics pass all constraints"""
        c = self.config.constraints
        
        if metrics['max_drawdown_pct'] > c.max_drawdown_pct:
            return False
        if metrics['sharpe_ratio'] < c.min_sharpe:
            return False
        if metrics['win_rate'] < c.min_win_rate:
            return False
        if metrics['profit_factor'] < c.min_profit_factor:
            return False
        if metrics['total_trades'] < c.min_trades:
            return False
        
        # Check risk:reward ratio
        if metrics['avg_loss'] > 0:
            rr_ratio = metrics['avg_win'] / metrics['avg_loss']
            if rr_ratio < c.min_rr_ratio:
                return False
        
        return True
    
    def _calculate_objective(self, metrics: Dict[str, float]) -> float:
        """Calculate objective function value"""
        obj = self.config.objective
        
        if obj == "sharpe":
            return metrics['sharpe_ratio']
        elif obj == "return":
            return metrics['total_return_pct']
        elif obj == "calmar":
            return metrics['calmar_ratio']
        elif obj == "sortino":
            return metrics['sortino_ratio']
        else:
            return metrics['sharpe_ratio']
