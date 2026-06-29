"""
Walk-Forward Analysis Engine
Rolling window optimization and out-of-sample testing
"""

from typing import List, Dict, Any, Optional, Type
from dataclasses import dataclass
from datetime import date, timedelta
import pandas as pd
import numpy as np
import logging

from ..backtest.engine import BacktestEngine, BacktestConfig, BacktestResult
from ..legacy_strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


@dataclass
class WFAWindow:
    """A single walk-forward window"""
    window_id: int
    train_start: date
    train_end: date
    test_start: date
    test_end: date
    train_result: Optional[BacktestResult] = None
    test_result: Optional[BacktestResult] = None
    optimized_params: Optional[Dict[str, Any]] = None


@dataclass
class WFAConfig:
    """Configuration for Walk-Forward Analysis"""
    symbol: str
    start_date: date
    end_date: date
    
    # Window configuration
    train_days: int = 252  # ~1 year of trading days
    test_days: int = 63    # ~3 months of trading days
    step_days: int = 63    # How much to advance for each window
    
    # Backtest settings
    initial_capital: float = 1000000.0
    is_intraday: bool = False
    
    # Optimization settings
    optimize: bool = False
    param_grid: Optional[Dict[str, List[Any]]] = None


@dataclass
class WFAResult:
    """Complete Walk-Forward Analysis result"""
    config: WFAConfig
    strategy_name: str
    windows: List[WFAWindow]
    
    # Aggregated metrics
    total_train_return: float = 0.0
    total_test_return: float = 0.0
    test_return_pct: float = 0.0
    avg_sharpe: float = 0.0
    robustness_ratio: float = 0.0  # Test performance / Train performance
    consistency: float = 0.0  # % of windows profitable
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'strategy_name': self.strategy_name,
            'symbol': self.config.symbol,
            'start_date': self.config.start_date.isoformat(),
            'end_date': self.config.end_date.isoformat(),
            'num_windows': len(self.windows),
            'total_train_return': round(self.total_train_return, 2),
            'total_test_return': round(self.total_test_return, 2),
            'test_return_pct': round(self.test_return_pct, 2),
            'avg_sharpe': round(self.avg_sharpe, 3),
            'robustness_ratio': round(self.robustness_ratio, 3),
            'consistency': round(self.consistency, 2),
        }


class WalkForwardEngine:
    """
    Walk-Forward Analysis Engine
    
    Performs rolling window backtests to assess strategy robustness:
    1. Split data into train/test windows
    2. Optimize parameters on training data (optional)
    3. Test on out-of-sample data
    4. Roll forward and repeat
    5. Aggregate results
    """
    
    def __init__(self, config: WFAConfig):
        self.config = config
        self._windows: List[WFAWindow] = []
    
    def generate_windows(self) -> List[WFAWindow]:
        """Generate train/test window pairs"""
        windows = []
        window_id = 0
        
        current_start = self.config.start_date
        
        while True:
            train_start = current_start
            train_end = train_start + timedelta(days=self.config.train_days)
            test_start = train_end + timedelta(days=1)
            test_end = test_start + timedelta(days=self.config.test_days)
            
            # Check if we've exceeded end date
            if test_end > self.config.end_date:
                break
            
            windows.append(WFAWindow(
                window_id=window_id,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end
            ))
            
            window_id += 1
            current_start += timedelta(days=self.config.step_days)
        
        self._windows = windows
        logger.info(f"Generated {len(windows)} walk-forward windows")
        return windows
    
    def run(
        self,
        strategy_class: Type[BaseStrategy],
        strategy_params: Dict[str, Any],
        data: pd.DataFrame
    ) -> WFAResult:
        """
        Run walk-forward analysis
        
        Args:
            strategy_class: Strategy class to instantiate
            strategy_params: Default strategy parameters
            data: Full dataset for all windows
            
        Returns:
            WFAResult with all window results and aggregated metrics
        """
        if not self._windows:
            self.generate_windows()
        
        if len(self._windows) == 0:
            raise ValueError("No windows generated. Check date range and window sizes.")
        
        logger.info(f"Running WFA with {len(self._windows)} windows")
        
        for window in self._windows:
            logger.info(f"Processing window {window.window_id}: "
                       f"Train {window.train_start} to {window.train_end}, "
                       f"Test {window.test_start} to {window.test_end}")
            
            # Get window parameters (optimize if enabled)
            if self.config.optimize and self.config.param_grid:
                params = self._optimize_window(
                    window, strategy_class, data
                )
                window.optimized_params = params
            else:
                params = strategy_params
            
            # Run training backtest
            train_result = self._run_backtest(
                strategy_class=strategy_class,
                params=params,
                data=data,
                start_date=window.train_start,
                end_date=window.train_end
            )
            window.train_result = train_result
            
            # Run testing backtest
            test_result = self._run_backtest(
                strategy_class=strategy_class,
                params=params,
                data=data,
                start_date=window.test_start,
                end_date=window.test_end
            )
            window.test_result = test_result
        
        # Calculate aggregated metrics
        result = self._aggregate_results(strategy_class.__name__)
        
        return result
    
    def _run_backtest(
        self,
        strategy_class: Type[BaseStrategy],
        params: Dict[str, Any],
        data: pd.DataFrame,
        start_date: date,
        end_date: date
    ) -> BacktestResult:
        """Run a single backtest for a window"""
        # Filter data for window
        mask = (data.index.date >= start_date) & (data.index.date <= end_date)
        window_data = data.loc[mask].copy()
        
        if len(window_data) == 0:
            raise ValueError(f"No data for period {start_date} to {end_date}")
        
        # Create backtest config
        config = BacktestConfig(
            symbol=self.config.symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.config.initial_capital,
            is_intraday=self.config.is_intraday
        )
        
        # Create and run backtest
        engine = BacktestEngine(config)
        engine.load_data(window_data)
        
        # Create strategy instance
        strategy = strategy_class(params)
        
        # Run backtest
        result = engine.run(strategy)
        
        return result
    
    def _optimize_window(
        self,
        window: WFAWindow,
        strategy_class: Type[BaseStrategy],
        data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Optimize parameters on training window only
        Simple grid search implementation
        """
        param_grid = self.config.param_grid
        
        best_params = None
        best_sharpe = float('-inf')
        
        # Generate all combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        
        from itertools import product
        
        for combo in product(*param_values):
            params = dict(zip(param_names, combo))
            
            try:
                result = self._run_backtest(
                    strategy_class=strategy_class,
                    params=params,
                    data=data,
                    start_date=window.train_start,
                    end_date=window.train_end
                )
                
                # Check guardrails
                if result.metrics.max_drawdown_pct > 25:  # Max 25% DD
                    continue
                if result.metrics.win_rate < 35:  # Min 35% win rate
                    continue
                
                if result.metrics.sharpe_ratio > best_sharpe:
                    best_sharpe = result.metrics.sharpe_ratio
                    best_params = params
                    
            except Exception as e:
                logger.warning(f"Optimization failed for params {params}: {e}")
                continue
        
        if best_params is None:
            logger.warning("No valid parameters found, using defaults")
            best_params = {k: v[0] for k, v in param_grid.items()}
        
        return best_params
    
    def _aggregate_results(self, strategy_name: str) -> WFAResult:
        """Aggregate results across all windows"""
        
        train_returns = []
        test_returns = []
        sharpes = []
        
        for window in self._windows:
            if window.train_result:
                train_returns.append(window.train_result.metrics.total_return)
            if window.test_result:
                test_returns.append(window.test_result.metrics.total_return)
                sharpes.append(window.test_result.metrics.sharpe_ratio)
        
        total_train = sum(train_returns)
        total_test = sum(test_returns)
        
        # Calculate metrics
        initial = self.config.initial_capital
        test_return_pct = (total_test / (initial * len(self._windows))) * 100 if self._windows else 0
        
        avg_sharpe = np.mean(sharpes) if sharpes else 0
        
        # Robustness ratio: how well does test compare to train?
        if total_train != 0:
            robustness = total_test / total_train
        else:
            robustness = 0
        
        # Consistency: % of windows profitable
        profitable_windows = sum(1 for r in test_returns if r > 0)
        consistency = (profitable_windows / len(test_returns) * 100) if test_returns else 0
        
        return WFAResult(
            config=self.config,
            strategy_name=strategy_name,
            windows=self._windows,
            total_train_return=total_train,
            total_test_return=total_test,
            test_return_pct=test_return_pct,
            avg_sharpe=avg_sharpe,
            robustness_ratio=robustness,
            consistency=consistency
        )
