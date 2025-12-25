"""
Walk-Forward Backtest API Router

Provides endpoints for Pardo-compliant walk-forward backtesting with:
- Rule-based strategies
- ML-based strategies (XGBoost/LSTM)
- Rolling IS/OOS window evaluation

New isolated module - does not modify existing APIs.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import logging

from utils.auth import get_optional_user
from models import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/backtest/walk-forward",
    tags=["Walk-Forward Backtest"]
)


# ============== Enums ==============

class StrategyType(str, Enum):
    RULE_BASED = "RULE_BASED"
    ML = "ML"


class TradeStyle(str, Enum):
    INTRADAY = "INTRADAY"
    SWING = "SWING"


class MLModel(str, Enum):
    NONE = "NONE"
    XGBOOST = "XGBOOST"
    LSTM = "LSTM"


class Timeframe(str, Enum):
    FIVE_MIN = "5m"
    FIFTEEN_MIN = "15m"
    THIRTY_MIN = "30m"
    ONE_HOUR = "1h"
    DAILY = "1D"


# ============== Request/Response Schemas ==============

class WalkForwardConfig(BaseModel):
    """Walk-forward window configuration"""
    train_window: int = Field(120, ge=20, description="Training window size (sessions/days)")
    test_window: int = Field(20, ge=5, description="Testing window size (sessions/days)")  
    step_size: int = Field(20, ge=5, description="Step size between windows")
    anchored: bool = Field(False, description="If true, training window starts from beginning")


class WalkForwardRequest(BaseModel):
    """Request schema for walk-forward backtest"""
    symbols: List[str] = Field(..., min_length=1, max_length=50, description="List of stock symbols")
    exchange: str = Field("NSE", description="Exchange (NSE)")
    strategy_type: StrategyType = Field(..., description="RULE_BASED or ML")
    strategy_name: str = Field(..., description="Strategy identifier")
    timeframe: Timeframe = Field(..., description="Candle timeframe")
    trade_style: TradeStyle = Field(..., description="INTRADAY or SWING")
    walk_forward: WalkForwardConfig = Field(default_factory=WalkForwardConfig)
    capital: float = Field(100000, gt=0, description="Initial capital")
    ml_model: MLModel = Field(MLModel.NONE, description="ML model type if strategy_type is ML")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbols": ["RELIANCE", "TCS"],
                "exchange": "NSE",
                "strategy_type": "RULE_BASED",
                "strategy_name": "trend_finder",
                "timeframe": "15m",
                "trade_style": "INTRADAY",
                "walk_forward": {
                    "train_window": 120,
                    "test_window": 20,
                    "step_size": 20,
                    "anchored": False
                },
                "capital": 100000,
                "ml_model": "NONE"
            }
        }


class WindowResult(BaseModel):
    """Results for a single walk-forward window"""
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


class ModelDiagnostics(BaseModel):
    """ML model diagnostics (if applicable)"""
    feature_importance: Optional[Dict[str, float]] = None
    confidence_decay: Optional[float] = None
    drift_detected: bool = False
    avg_prediction_confidence: Optional[float] = None


class WalkForwardSummary(BaseModel):
    """Aggregated summary metrics"""
    total_return: float
    cagr: Optional[float] = None
    sharpe: float
    sortino: Optional[float] = None
    max_drawdown: float
    win_rate: float
    profitable_windows_pct: float
    parameter_stability_score: Optional[float] = None
    expectancy: Optional[float] = None


class WalkForwardResponse(BaseModel):
    """Response schema for walk-forward backtest"""
    summary: WalkForwardSummary
    oos_equity_curve: List[Dict[str, Any]]
    window_results: List[WindowResult]
    best_parameters_by_window: List[Dict[str, Any]]
    model_diagnostics: Optional[ModelDiagnostics] = None
    validation_passed: bool
    validation_messages: List[str]
    run_timestamp: str
    duration_seconds: float


# ============== Endpoints ==============

@router.post("", response_model=WalkForwardResponse)
async def run_walk_forward_backtest(
    request: WalkForwardRequest,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Run a Pardo-compliant Walk-Forward Backtest
    
    This endpoint performs statistically valid strategy evaluation using:
    - Rolling In-Sample (IS) windows for optimization/training
    - Out-of-Sample (OOS) windows for unbiased evaluation
    - Stitched OOS equity curves
    
    **No data leakage**: IS metrics are never exposed, only OOS results.
    
    **Auto-fail conditions**:
    - Less than 60% profitable windows
    - Excessive parameter instability
    - Sharp performance decay
    """
    import time
    start_time = time.time()
    
    try:
        # Import service here to avoid circular imports
        from services.walk_forward_backtest_service import WalkForwardBacktestService
        
        service = WalkForwardBacktestService()
        result = await service.run_backtest(request)
        
        result.duration_seconds = time.time() - start_time
        result.run_timestamp = datetime.now().isoformat()
        
        return result
        
    except ValueError as e:
        logger.error(f"Validation error in walk-forward backtest: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error running walk-forward backtest: {e}")
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


@router.get("/strategies")
async def get_available_strategies():
    """Get list of available strategies for walk-forward backtesting"""
    return {
        "rule_based": [
            {"name": "trend_finder", "description": "EMA crossover with ADX filter"},
            {"name": "breakout_detector", "description": "Price breakout with volume confirmation"},
            {"name": "momentum", "description": "RSI + ROC momentum strategy"},
            {"name": "mean_reversion", "description": "Bollinger Band mean reversion"},
            {"name": "gap_scanner", "description": "Gap-up/down continuation strategy"},
            {"name": "vwap_bounce", "description": "VWAP support/resistance strategy"},
            {"name": "sr_bounce", "description": "Support/Resistance bounce strategy"},
        ],
        "ml": [
            {"name": "xgboost_classifier", "description": "XGBoost binary classification"},
            {"name": "lstm_sequence", "description": "LSTM sequence prediction"},
        ]
    }


@router.get("/presets")
async def get_walk_forward_presets():
    """Get recommended walk-forward configurations by trade style"""
    return {
        "intraday": {
            "train_window": 60,
            "test_window": 10,
            "step_size": 10,
            "description": "60 sessions train, 10 sessions test, frequent re-optimization"
        },
        "swing": {
            "train_window": 252,
            "test_window": 63,
            "step_size": 21,
            "description": "1 year train, 3 months test, monthly step"
        }
    }
