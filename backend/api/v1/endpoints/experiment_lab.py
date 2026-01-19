"""
API Endpoints for Strategy Experiment Lab (Beta)
⚠️ BACKTESTING / SIMULATION ONLY - NO LIVE TRADING
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

# Import experiment lab components
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from experiment_lab.registry import StrategyRegistry, STRATEGY_CATALOG
from experiment_lab.engine.backtest_runner import ExperimentRunner, BacktestConfig
from experiment_lab.engine.comparison_engine import ComparisonEngine


router = APIRouter(
    prefix="/api/v1/experiment-lab",
    tags=["Experiment Lab (Beta)"]
)


# ==================== Request/Response Models ====================

class BacktestRequest(BaseModel):
    """Request model for running a backtest."""
    symbol: str = Field(..., description="Stock symbol (e.g., RELIANCE)")
    strategy_ids: List[int] = Field(..., description="List of strategy IDs (1-70)")
    timeframe: str = Field(default="1D", description="Timeframe: 5m, 15m, 30m, 1H, 1D")
    start_date: str = Field(default=None, description="Start date (YYYY-MM-DD)")
    end_date: str = Field(default=None, description="End date (YYYY-MM-DD)")
    initial_capital: float = Field(default=1000000, description="Initial capital in INR")
    risk_mode: str = Field(default="percent_capital", description="Risk mode: fixed_quantity, fixed_amount, percent_capital, atr_based")
    risk_percent: float = Field(default=2.0, description="Risk per trade (%)")
    max_holding_bars: int = Field(default=20, description="Maximum bars to hold a position")


class StrategyInfo(BaseModel):
    """Strategy information model."""
    id: int
    name: str
    category: str
    description: str


class CategoryInfo(BaseModel):
    """Category information model."""
    id: str
    name: str
    count: int


# ==================== API Endpoints ====================

@router.get("/")
async def get_lab_info():
    """
    Get experiment lab information and status.
    ⚠️ BACKTESTING / SIMULATION ONLY
    """
    return {
        "name": "Strategy Experiment Lab",
        "version": "1.0.0-beta",
        "status": "active",
        "disclaimer": "⚠️ BACKTESTING / SIMULATION ONLY - NO LIVE TRADING",
        "total_strategies": 70,
        "categories": 10,
        "features": [
            "70 predefined strategy combinations",
            "Multiple timeframes: 5m, 15m, 30m, 1H, 1D",
            "Comprehensive performance metrics",
            "Multi-strategy comparison",
            "Position sizing: Fixed, Percent, ATR-based"
        ]
    }


@router.get("/strategies", response_model=List[StrategyInfo])
async def list_strategies(
    category: Optional[str] = Query(None, description="Filter by category (A-J)")
):
    """
    List all available strategies or filter by category.
    """
    strategies = STRATEGY_CATALOG
    
    if category:
        strategies = [s for s in strategies if s['category'].upper() == category.upper()]
    
    return strategies


@router.get("/strategies/{strategy_id}")
async def get_strategy(strategy_id: int):
    """
    Get detailed information about a specific strategy.
    """
    strategy_info = next(
        (s for s in STRATEGY_CATALOG if s['id'] == strategy_id),
        None
    )
    
    if not strategy_info:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    
    # Get additional info from strategy class
    strategy_instance = StrategyRegistry.instantiate(strategy_id)
    additional_info = {}
    
    if strategy_instance:
        info = strategy_instance.info
        additional_info = {
            "indicators_used": info.indicators_used,
            "min_bars_required": info.min_bars_required
        }
    
    return {
        **strategy_info,
        **additional_info
    }


@router.get("/categories", response_model=List[CategoryInfo])
async def list_categories():
    """
    List all strategy categories with descriptions.
    """
    return StrategyRegistry.get_categories()


@router.post("/backtest")
async def run_backtest(request: BacktestRequest):
    """
    Run backtest for one or more strategies.
    ⚠️ SIMULATION ONLY - Results are hypothetical.
    
    Returns comprehensive metrics including:
    - Total Return, CAGR
    - Max Drawdown
    - Sharpe, Sortino, Calmar ratios
    - Win Rate, Profit Factor
    - Equity curve
    """
    # Validate strategy IDs
    valid_ids = {s['id'] for s in STRATEGY_CATALOG}
    invalid_ids = [sid for sid in request.strategy_ids if sid not in valid_ids]
    if invalid_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy IDs: {invalid_ids}. Valid range: 1-70"
        )
    
    # Default dates if not provided
    end_date = request.end_date or datetime.now().strftime("%Y-%m-%d")
    start_date = request.start_date or (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    # Create config
    config = BacktestConfig(
        symbol=request.symbol.upper(),
        strategy_ids=request.strategy_ids,
        timeframe=request.timeframe,
        start_date=start_date,
        end_date=end_date,
        initial_capital=request.initial_capital,
        risk_mode=request.risk_mode,
        risk_percent=request.risk_percent,
        max_holding_bars=request.max_holding_bars
    )
    
    # Run backtest
    try:
        runner = ExperimentRunner()
        results = runner.run_backtest(config)
        
        if not results:
            raise HTTPException(
                status_code=400,
                detail="No results generated. Check if strategies are valid."
            )
        
        # Format response
        return {
            "disclaimer": "⚠️ BACKTESTING / SIMULATION ONLY - Past performance does not guarantee future results",
            "config": {
                "symbol": config.symbol,
                "timeframe": config.timeframe,
                "start_date": start_date,
                "end_date": end_date,
                "initial_capital": config.initial_capital,
                "risk_mode": config.risk_mode,
                "risk_percent": config.risk_percent
            },
            "results": [r.to_dict() for r in results],
            "total_strategies": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


@router.post("/compare")
async def compare_strategies(request: BacktestRequest):
    """
    Run backtests for multiple strategies and compare results.
    Returns rankings by different criteria.
    """
    if len(request.strategy_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 strategies required for comparison"
        )
    
    # Validate strategy IDs
    valid_ids = {s['id'] for s in STRATEGY_CATALOG}
    invalid_ids = [sid for sid in request.strategy_ids if sid not in valid_ids]
    if invalid_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy IDs: {invalid_ids}"
        )
    
    # Default dates
    end_date = request.end_date or datetime.now().strftime("%Y-%m-%d")
    start_date = request.start_date or (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    config = BacktestConfig(
        symbol=request.symbol.upper(),
        strategy_ids=request.strategy_ids,
        timeframe=request.timeframe,
        start_date=start_date,
        end_date=end_date,
        initial_capital=request.initial_capital,
        risk_mode=request.risk_mode,
        risk_percent=request.risk_percent,
        max_holding_bars=request.max_holding_bars
    )
    
    try:
        runner = ExperimentRunner()
        results = runner.run_backtest(config)
        
        # Compare results
        comparison_engine = ComparisonEngine()
        comparison = comparison_engine.compare(results)
        
        return {
            "disclaimer": "⚠️ BACKTESTING / SIMULATION ONLY",
            "config": {
                "symbol": config.symbol,
                "timeframe": config.timeframe,
                "start_date": start_date,
                "end_date": end_date
            },
            "comparison": comparison
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.get("/symbols")
async def get_available_symbols(
    timeframe: str = Query("1D", description="Timeframe: 5m, 15m, 30m, 1H, 1D")
):
    """
    Get list of symbols available for backtesting for a given timeframe.
    """
    # Try to get symbols from database
    try:
        from services.db_data_fetcher import get_db_data_fetcher
        fetcher = get_db_data_fetcher()
        symbols = fetcher.get_available_symbols(timeframe=timeframe)
        if symbols:
            return {
                "symbols": symbols, 
                "count": len(symbols),
                "timeframe": timeframe,
                "source": "database"
            }
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Experiment Lab symbols error: {e}")
    
    # Fallback to common Nifty stocks
    default_symbols = [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "HINDUNILVR", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK",
        "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "BAJFINANCE",
        "HCLTECH", "WIPRO", "ULTRACEMCO", "TITAN", "NESTLEIND"
    ]
    
    return {
        "symbols": default_symbols, 
        "count": len(default_symbols),
        "timeframe": timeframe,
        "source": "default_fallback"
    }


@router.get("/timeframes")
async def get_available_timeframes():
    """
    Get list of supported timeframes.
    """
    return {
        "timeframes": [
            {"id": "5m", "name": "5 Minutes", "description": "Intraday - High frequency"},
            {"id": "15m", "name": "15 Minutes", "description": "Intraday - Medium frequency"},
            {"id": "30m", "name": "30 Minutes", "description": "Intraday - Lower frequency"},
            {"id": "1H", "name": "1 Hour", "description": "Intraday/Swing"},
            {"id": "1D", "name": "Daily", "description": "Daily candles - Most reliable"}
        ]
    }


@router.delete("/cache")
async def clear_cache():
    """
    Clear the backtest result cache.
    """
    runner = ExperimentRunner()
    runner.clear_cache()
    return {"message": "Cache cleared successfully"}


__all__ = ['router']
