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
import sqlite3
import os

from utils.auth import get_current_user, get_current_user
from models import User
from typing import Optional as TypingOptional
from database import AsyncSessionLocal
from models_alpha import StockCandle, StockCandleV2, InstrumentMaster, TimeframeMapper
from sqlalchemy import select, func

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/walk-forward",
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
    current_user: User = Depends(get_current_user)
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
async def get_available_strategies(current_user: User = Depends(get_current_user)):
    """Get list of available strategies for walk-forward backtesting with full parameter details"""
    return {
        "Trend & Momentum": [
            {
                "name": "ma_crossover",
                "display_name": "Moving Average Crossover",
                "description": "Classic SMA/EMA crossover strategy with trend confirmation",
                "parameters": {
                    "fast_period": {"type": "int", "default": 9, "min": 5, "max": 50},
                    "slow_period": {"type": "int", "default": 21, "min": 10, "max": 200},
                    "ma_type": {"type": "select", "default": "EMA", "options": ["SMA", "EMA"]},
                    "atr_multiplier": {"type": "float", "default": 2.0, "min": 1.0, "max": 5.0},
                    "risk_reward": {"type": "float", "default": 2.0, "min": 1.0, "max": 5.0}
                },
                "time_horizon": "Swing"
            },
            {
                "name": "supertrend",
                "display_name": "SuperTrend",
                "description": "ATR-based trailing stop system that identifies trend direction",
                "parameters": {
                    "period": {"type": "int", "default": 10, "min": 5, "max": 50},
                    "multiplier": {"type": "float", "default": 3.0, "min": 1.0, "max": 5.0},
                    "risk_reward": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0}
                },
                "time_horizon": "Swing"
            },
            {
                "name": "adx_trend",
                "display_name": "ADX Trend Following",
                "description": "Enter trades only when trend strength is confirmed by ADX",
                "parameters": {
                    "adx_period": {"type": "int", "default": 14, "min": 7, "max": 30},
                    "adx_threshold": {"type": "int", "default": 25, "min": 15, "max": 40},
                    "atr_multiplier": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0},
                    "risk_reward": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0}
                },
                "time_horizon": "Swing"
            },
            {
                "name": "donchian_breakout",
                "display_name": "Donchian Channel Breakout",
                "description": "Classic turtle trading breakout strategy using price channels",
                "parameters": {
                    "entry_period": {"type": "int", "default": 20, "min": 10, "max": 55},
                    "exit_period": {"type": "int", "default": 10, "min": 5, "max": 30},
                    "atr_period": {"type": "int", "default": 14, "min": 7, "max": 21}
                },
                "time_horizon": "Positional"
            }
        ],
        "Mean Reversion": [
            {
                "name": "rsi_mean_reversion",
                "display_name": "RSI Mean Reversion",
                "description": "Trade reversals when RSI indicates extreme conditions",
                "parameters": {
                    "rsi_period": {"type": "int", "default": 14, "min": 7, "max": 21},
                    "oversold": {"type": "int", "default": 30, "min": 20, "max": 40},
                    "overbought": {"type": "int", "default": 70, "min": 60, "max": 80},
                    "atr_multiplier": {"type": "float", "default": 1.5, "min": 1.0, "max": 3.0},
                    "risk_reward": {"type": "float", "default": 1.5, "min": 1.0, "max": 3.0}
                },
                "time_horizon": "Swing"
            },
            {
                "name": "bollinger_reversion",
                "display_name": "Bollinger Bands Reversion",
                "description": "Trade reversals at Bollinger Band extremes",
                "parameters": {
                    "period": {"type": "int", "default": 20, "min": 10, "max": 50},
                    "std_dev": {"type": "float", "default": 2.0, "min": 1.5, "max": 3.0},
                    "risk_reward": {"type": "float", "default": 1.5, "min": 1.0, "max": 3.0}
                },
                "time_horizon": "Swing"
            },
            {
                "name": "zscore_reversion",
                "display_name": "Z-Score Price Reversion",
                "description": "Statistical mean reversion using z-score of price",
                "parameters": {
                    "lookback": {"type": "int", "default": 20, "min": 10, "max": 60},
                    "entry_threshold": {"type": "float", "default": 2.0, "min": 1.5, "max": 3.0},
                    "exit_threshold": {"type": "float", "default": 0.5, "min": 0.0, "max": 1.0},
                    "atr_multiplier": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0}
                },
                "time_horizon": "Swing"
            }
        ],
        "Breakout & Volatility": [
            {
                "name": "orb",
                "display_name": "Opening Range Breakout",
                "description": "Trade breakouts from the first N minutes of trading",
                "parameters": {
                    "orb_minutes": {"type": "int", "default": 15, "min": 5, "max": 60},
                    "buffer_pct": {"type": "float", "default": 0.1, "min": 0.0, "max": 0.5},
                    "risk_reward": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0}
                },
                "time_horizon": "Intraday"
            },
            {
                "name": "volume_breakout",
                "display_name": "Volume Breakout",
                "description": "Trade price breakouts confirmed by volume surge",
                "parameters": {
                    "price_period": {"type": "int", "default": 20, "min": 10, "max": 50},
                    "volume_period": {"type": "int", "default": 20, "min": 10, "max": 50},
                    "volume_mult": {"type": "float", "default": 1.5, "min": 1.2, "max": 3.0},
                    "atr_multiplier": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0}
                },
                "time_horizon": "Swing"
            },
            {
                "name": "atr_expansion",
                "display_name": "ATR Volatility Expansion",
                "description": "Trade volatility expansion after contraction periods",
                "parameters": {
                    "atr_period": {"type": "int", "default": 14, "min": 7, "max": 21},
                    "expansion_mult": {"type": "float", "default": 1.5, "min": 1.2, "max": 2.5},
                    "lookback": {"type": "int", "default": 20, "min": 10, "max": 50},
                    "risk_reward": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0}
                },
                "time_horizon": "Swing"
            }
        ],
        "VWAP & Institutional": [
            {
                "name": "vwap_pullback",
                "display_name": "VWAP Pullback",
                "description": "Trade pullbacks to VWAP when price is trending",
                "parameters": {
                    "trend_ema": {"type": "int", "default": 20, "min": 10, "max": 50},
                    "vwap_buffer": {"type": "float", "default": 0.1, "min": 0.05, "max": 0.5},
                    "atr_multiplier": {"type": "float", "default": 1.5, "min": 1.0, "max": 3.0},
                    "risk_reward": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0}
                },
                "time_horizon": "Intraday"
            },
            {
                "name": "vwap_trend",
                "display_name": "VWAP Trend Confirmation",
                "description": "Use VWAP as institutional reference for trend direction",
                "parameters": {
                    "confirmation_bars": {"type": "int", "default": 3, "min": 1, "max": 10},
                    "atr_multiplier": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0},
                    "risk_reward": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0}
                },
                "time_horizon": "Intraday"
            }
        ]
    }


@router.get("/presets")
async def get_walk_forward_presets(current_user: User = Depends(get_current_user)):
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


@router.get("/symbols")
async def get_available_symbols(
    timeframe: str = "1D",
    current_user: User = Depends(get_current_user)
):
    tf_minutes = TimeframeMapper.to_minutes(timeframe)
    
    try:
        async with AsyncSessionLocal() as session:
            # Query distinct symbols by joining with InstrumentMaster
            query = (
                select(InstrumentMaster.symbol)
                .join(StockCandleV2, StockCandleV2.instrument_id == InstrumentMaster.instrument_id)
                .where(StockCandleV2.timeframe == tf_minutes)
                .distinct()
                .order_by(InstrumentMaster.symbol)
            )
            result = await session.execute(query)
            symbols = [row[0] for row in result.all()]
            
            return {
                "symbols": symbols,
                "count": len(symbols),
                "timeframe": timeframe,
                "tf_minutes": tf_minutes,
                "source": "postgresql_v2_async",
                "debug": {
                    "tf_minutes_type": str(type(tf_minutes)),
                    "query_exec": True
                }
            }
    except Exception as e:
        logger.error(f"Error fetching symbols via V2 schema: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch available symbols")



