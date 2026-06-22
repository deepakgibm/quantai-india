from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any, Optional
import logging

from database import get_read_db
from models import User
from utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Walk-Forward Backtest"])


# ==================== Pydantic Models for Import Compatibility ====================

class WalkForwardSummary(BaseModel):
    total_return: float
    sharpe: float
    max_drawdown: float
    win_rate: float
    profitable_windows_pct: float


class ModelDiagnostics(BaseModel):
    feature_importance: Dict[str, float]
    confidence_decay: float
    drift_detected: bool
    avg_prediction_confidence: float


class WindowResult(BaseModel):
    window_id: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    oos_return: float
    oos_sharpe: float
    oos_max_drawdown: float
    oos_win_rate: float
    oos_trade_count: int
    parameters: Dict[str, Any]


class WalkForwardResponse(BaseModel):
    summary: WalkForwardSummary
    oos_equity_curve: List[Any]
    window_results: List[WindowResult]
    best_parameters_by_window: List[Dict[str, Any]]
    model_diagnostics: Optional[ModelDiagnostics] = None
    validation_passed: bool
    validation_messages: List[str]
    run_timestamp: str = ""
    duration_seconds: float = 0.0


# ==================== Endpoints ====================

@router.get("/symbols")
async def get_walk_forward_symbols(
    timeframe: str = Query("1D"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db)
):
    """
    Get list of available symbols for walk-forward backtest.
    """
    try:
        # Fetch active NSE symbols from instrument_master
        sql = text("""
            SELECT DISTINCT symbol 
            FROM instrument_master 
            WHERE is_active = TRUE AND exchange = 'NSE'
            ORDER BY symbol ASC
        """)
        res = await db.execute(sql)
        symbols = [r[0] for r in res.fetchall()]
        
        # If DB is empty, use standard F&O stocks fallback list
        if not symbols:
            from data.fno_stocks import get_fno_stocks
            symbols = get_fno_stocks()
            
        return {
            "success": True,
            "symbols": symbols
        }
    except Exception as e:
        logger.error(f"Error fetching walk-forward symbols: {e}")
        # Final fallback
        from data.fno_stocks import get_fno_stocks
        return {
            "success": True,
            "symbols": get_fno_stocks()
        }


@router.get("/strategies")
async def get_walk_forward_strategies(
    current_user: User = Depends(get_current_user)
):
    """
    Get list of available strategies for walk-forward backtest.
    """
    try:
        from core.backtest.strategies_impl import StrategyRegistry as CoreStrategyRegistry
        from experiment_lab.registry import STRATEGY_CATALOG
        
        strategies = []
        try:
            categories_dict = CoreStrategyRegistry.list_by_category()
            for cat_name, strats in categories_dict.items():
                for s in strats:
                    strategies.append({
                        "id": s.name,
                        "name": s.display_name,
                        "category": cat_name,
                        "description": s.description
                    })
        except Exception:
            pass
            
        for s in STRATEGY_CATALOG:
            strategies.append({
                "id": str(s["id"]),
                "name": s["name"],
                "category": f"Experiment - {s['category']}",
                "description": s["description"]
            })
            
        return {
            "success": True,
            "strategies": strategies
        }
    except Exception as e:
        logger.error(f"Error listing walk-forward strategies: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/presets")
async def get_walk_forward_presets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db)
):
    """
    Get list of presets for walk-forward backtesting parameters.
    """
    presets = [
        {
            "id": "ma_sweep",
            "name": "MA Parameter Sweep",
            "strategy_id": "ma_crossover",
            "param_grid": [
                {"fast_period": 9, "slow_period": 21},
                {"fast_period": 9, "slow_period": 50},
                {"fast_period": 20, "slow_period": 50},
                {"fast_period": 20, "slow_period": 100}
            ],
            "train_window_bars": 120,
            "test_window_bars": 30,
            "step_bars": 30
        },
        {
            "id": "rsi_sweep",
            "name": "RSI Threshold Sweep",
            "strategy_id": "rsi_reversal",
            "param_grid": [
                {"rsi_period": 14, "rsi_lower": 30, "rsi_upper": 70},
                {"rsi_period": 14, "rsi_lower": 25, "rsi_upper": 75},
                {"rsi_period": 10, "rsi_lower": 30, "rsi_upper": 70}
            ],
            "train_window_bars": 120,
            "test_window_bars": 30,
            "step_bars": 30
        }
    ]
    return {
        "success": True,
        "presets": presets
    }
