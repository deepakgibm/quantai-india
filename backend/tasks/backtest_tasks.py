"""
Backtest Celery Tasks

Runs backtests asynchronously via Celery worker, freeing the API server
from blocking on long-running computations.
"""

import json
import logging
from datetime import date, datetime
from typing import Dict, Any, Optional

from celery import current_task
from celery_app import celery_app
from core.backtest.engine import BacktestEngine, BacktestConfig
from core.backtest.vectorized_engine import VectorizedBacktestEngine

logger = logging.getLogger(__name__)


def _publish_backtest_progress(task_id: str, status: str, progress: float = 0.0, **extra):
    """Publish backtest progress to DragonflyDB for UI polling."""
    meta = {
        "status": status,
        "progress": progress,
        "task_id": task_id,
        "updated_at": datetime.now().isoformat(),
        **extra,
    }
    
    if current_task:
        current_task.update_state(state="PROGRESS", meta=meta)
    
    try:
        from services.dragonfly_client import get_cache
        cache = get_cache()
        if cache.is_available():
            cache.set(f"qai:backtest:progress:{task_id}", json.dumps(meta), ttl=3600)
    except Exception:
        pass


@celery_app.task(
    bind=True,
    name="tasks.backtest_tasks.run_backtest",
    soft_time_limit=120,    # 2 min soft limit
    time_limit=300,         # 5 min hard kill
    max_retries=0,
    acks_late=True,
)
def run_backtest(self, config: Dict[str, Any]):
    """
    Run a backtest asynchronously via Celery.
    
    Args:
        config: Backtest configuration dict with keys:
            - symbol: str
            - start_date: str (YYYY-MM-DD)
            - end_date: str (YYYY-MM-DD)
            - strategy_name: str
            - strategy_params: dict
            - initial_capital: float (default: 1000000)
            - is_intraday: bool (default: False)
            
    Returns:
        dict with backtest results
    """
    task_id = self.request.id
    logger.info(f"[Backtest {task_id}] Starting: {config.get('symbol')} / {config.get('strategy_name')}")
    
    _publish_backtest_progress(task_id, "loading_data", 0.1)
    
    try:
        # Parse configuration
        start = date.fromisoformat(config["start_date"])
        end = date.fromisoformat(config["end_date"])
        
        bt_config = BacktestConfig(
            symbol=config["symbol"],
            start_date=start,
            end_date=end,
            initial_capital=config.get("initial_capital", 1_000_000.0),
            is_intraday=config.get("is_intraday", False),
        )
        
        # Select Engine
        engine_type = config.get("engine_type", "event_driven")
        if engine_type == "vectorized":
            engine = VectorizedBacktestEngine(bt_config)
        else:
            engine = BacktestEngine(bt_config)
        
        _publish_backtest_progress(task_id, "loading_data", 0.2)
        
        # Load data
        if engine_type == "vectorized":
            # Direct Parquet Loading
            pass # Engine handles it in run() or we can call it here
        else:
            # Load data from database using a sync session
            from database import SessionLocal
            session = SessionLocal()
            try:
                engine.load_data_from_db(session)
            finally:
                session.close()
        
        _publish_backtest_progress(task_id, "running_strategy", 0.4)
        
        # Load strategy
        strategy_name = config.get("strategy_name", "RSIMeanReversion")
        strategy_params = config.get("strategy_params", {})
        
        # Dynamic strategy loading based on engine type
        if engine_type == "vectorized":
            strategy = _load_vectorized_strategy(strategy_name, strategy_params)
        else:
            strategy = _load_strategy(strategy_name, strategy_params)
        
        if strategy is None:
            _publish_backtest_progress(task_id, "error", 0.0, error=f"Unknown strategy: {strategy_name}")
            return {"status": "error", "error": f"Unknown strategy: {strategy_name}"}
        
        _publish_backtest_progress(task_id, "computing_metrics", 0.7)
        
        # Run the backtest
        result = engine.run(strategy)
        
        _publish_backtest_progress(task_id, "completed", 1.0)
        
        # Serialize result
        result_dict = result.to_dict()
        
        # Cache the result in DragonflyDB for fast retrieval
        try:
            from services.dragonfly_client import get_cache
            cache = get_cache()
            if cache.is_available():
                cache.set(
                    f"qai:backtest:result:{task_id}", 
                    json.dumps(result_dict, default=str), 
                    ttl=7200  # Cache for 2 hours
                )
        except Exception as e:
            logger.warning(f"Failed to cache backtest result: {e}")
        
        logger.info(f"[Backtest {task_id}] Completed: return={result.metrics.total_return_pct:.2f}%")
        
        return {
            "status": "completed",
            "task_id": task_id,
            "metrics": result.metrics.to_dict(),
            "trade_count": len(result.trades),
            "duration_seconds": result.duration_seconds,
        }
        
    except Exception as e:
        logger.error(f"[Backtest {task_id}] Failed: {e}", exc_info=True)
        _publish_backtest_progress(task_id, "error", 0.0, error=str(e))
        raise


def _load_strategy(strategy_name: str, params: Dict[str, Any]) -> Optional[Any]:
    """Dynamically load a strategy by name."""
    try:
        from core.legacy_strategies import get_strategy
        
        # Map common strategy names to internal names
        name_map = {
            "RSIMeanReversion": "RSIMeanReversion",
            "MACDCrossover": "MACDCrossover",
            "BollingerBands": "BollingerSqueeze",
            "BollingerSqueeze": "BollingerSqueeze",
            "Supertrend": "Supertrend",
            "Stochastic": "Stochastic",
            "ADXTrend": "ADXTrend",
            "VolumeBreakout": "VolumeBreakout",
            "Ichimoku": "Ichimoku",
            "MACrossover": "MACrossover",
        }
        
        internal_name = name_map.get(strategy_name, strategy_name)
        return get_strategy(internal_name, params)
    except Exception as e:
        logger.error(f"Failed to load strategy '{strategy_name}': {e}")
        return None
def _load_vectorized_strategy(strategy_name: str, params: Dict[str, Any]) -> Optional[Any]:
    """Dynamically load a vectorized strategy by name."""
    try:
        import importlib
        
        strategy_map = {
            "RSIVectorized": ("core.backtest.strategies.rsi_vectorized", "RSIVectorizedStrategy"),
        }
        
        if strategy_name in strategy_map:
            module_path, class_name = strategy_map[strategy_name]
            module = importlib.import_module(module_path)
            strategy_class = getattr(module, class_name)
            return strategy_class(**params)
            
        # Fallback to direct import in vectorized folder
        module = importlib.import_module(f"core.backtest.strategies.{strategy_name.lower()}")
        strategy_class = getattr(module, f"{strategy_name}Strategy")
        return strategy_class(**params)
    except Exception as e:
        logger.error(f"Failed to load vectorized strategy '{strategy_name}': {e}")
        return None
