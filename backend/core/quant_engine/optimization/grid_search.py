"""
Parameter Optimization Engine
Executes grid search sweeps across parameter configurations in parallel.
"""

from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict, Any, Type, Tuple
import pandas as pd
import time
import logging

from ..strategy.base import UnifiedStrategy
from ..execution.vectorized import VectorizedExecutionEngine

logger = logging.getLogger(__name__)


def _run_single_backtest(
    strategy_class_path: Tuple[str, str],
    params: Dict[str, Any],
    df_dict: Dict[str, Any],
    initial_capital: float
) -> Dict[str, Any]:
    """
    Pickle-friendly helper function executed in a separate process.
    Re-imports the strategy class inside the process to avoid unpickleable issues.
    """
    import importmodule_hack
    import pandas as pd
    
    # Dynamically import strategy class
    import importlib
    module_name, class_name = strategy_class_path
    module = importlib.import_module(module_name)
    strategy_class = getattr(module, class_name)
    
    df = pd.DataFrame(df_dict)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
    strategy = strategy_class(params)
    engine = VectorizedExecutionEngine(initial_capital)
    
    try:
        res = engine.run(strategy, df)
        return {
            "params": params,
            "metrics": {
                "total_return_pct": res.get("total_return_pct", 0.0),
                "sharpe_ratio": res.get("sharpe_ratio", 0.0),
                "max_drawdown_pct": res.get("max_drawdown_pct", 0.0),
                "total_trades": res.get("total_trades", 0),
                "win_rate": res.get("win_rate", 0.0),
                "profit_factor": res.get("profit_factor", 0.0)
            },
            "status": "success"
        }
    except Exception as e:
        return {
            "params": params,
            "error": str(e),
            "status": "failed"
        }


class ParameterOptimizer:
    """
    Strategy Optimization Engine.
    Executes parallel parameter sweeps to identify optimal performance sets.
    """

    def __init__(self, initial_capital: float = 1000000.0):
        self.initial_capital = initial_capital

    def optimize_grid(
        self,
        strategy_module: str,
        strategy_class_name: str,
        df: pd.DataFrame,
        param_grid: List[Dict[str, Any]],
        max_workers: int = 4
    ) -> Dict[str, Any]:
        """
        Runs parallel grid search over parameter list.
        """
        start_time = time.time()
        
        # Convert DataFrame to dictionary to allow clean multiprocessing pickling
        df_dict = df.to_dict(orient="list")
        strategy_class_path = (strategy_module, strategy_class_name)
        
        results = []
        logger.info(f"Starting parameter optimization: {len(param_grid)} iterations.")
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _run_single_backtest,
                    strategy_class_path,
                    params,
                    df_dict,
                    self.initial_capital
                ): params
                for params in param_grid
            }
            
            for fut in as_completed(futures):
                res = fut.result()
                results.append(res)

        duration = time.time() - start_time
        successful_runs = [r for r in results if r["status"] == "success"]
        
        # Rank by Sharpe Ratio descending
        successful_runs.sort(key=lambda x: x["metrics"]["sharpe_ratio"], reverse=True)
        
        best_run = successful_runs[0] if successful_runs else None

        return {
            "total_runs": len(param_grid),
            "duration_seconds": round(duration, 4),
            "best_run": best_run,
            "all_runs": successful_runs[:50]  # Return top 50 runs for visualization
        }
