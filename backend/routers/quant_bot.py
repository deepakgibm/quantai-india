"""
Quant Bot API Router
FastAPI endpoints for backtesting, WFA, and quant operations
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
import pandas as pd
import logging
import numpy as np

from sqlalchemy.orm import Session
from database import get_db

# New strategy system imports
from core.backtest.strategies_impl import StrategyRegistry
from core.backtest.costs import OrderSide
from core.backtest.executor import OrderType

logger = logging.getLogger(__name__)

router = APIRouter()


# =====================
# Request/Response Models
# =====================

class BacktestRequest(BaseModel):
    """Request model for running a backtest"""
    symbol: str = Field(..., description="Stock symbol (e.g., 'RELIANCE')")
    strategy: str = Field("MACrossover", description="Strategy name")
    start_date: date = Field(..., description="Backtest start date")
    end_date: date = Field(..., description="Backtest end date")
    initial_capital: float = Field(1000000.0, description="Starting capital")
    params: Optional[Dict[str, Any]] = Field(None, description="Strategy parameters")


class BacktestResponse(BaseModel):
    """Response model for backtest results"""
    status: str
    run_id: str
    strategy: str
    symbol: str
    metrics: Dict[str, Any]
    trade_count: int
    duration_seconds: float


class WFARequest(BaseModel):
    """Request model for walk-forward analysis"""
    symbol: str = Field(..., description="Stock symbol")
    strategy: str = Field("MACrossover", description="Strategy name")
    start_date: date = Field(..., description="Start date")
    end_date: date = Field(..., description="End date")
    train_days: int = Field(252, description="Training window in days")
    test_days: int = Field(63, description="Testing window in days")
    initial_capital: float = Field(1000000.0, description="Starting capital")
    params: Optional[Dict[str, Any]] = Field(None, description="Strategy parameters")
    optimize: bool = Field(False, description="Whether to optimize parameters")


class WFAResponse(BaseModel):
    """Response model for WFA results"""
    status: str
    strategy: str
    symbol: str
    num_windows: int
    total_test_return: float
    test_return_pct: float
    avg_sharpe: float
    robustness_ratio: float
    consistency: float


class StrategyListResponse(BaseModel):
    """Response model for available strategies"""
    strategies: List[Dict[str, Any]]


# =====================
# Helper Functions
# =====================

class NewStrategyAdapter:
    """Adapter to run vectorized strategies in the event-driven BacktestEngine"""
    def __init__(self, strategy_instance, params):
        self.strategy_instance = strategy_instance
        self.params = params
        self.signals_df = None
        self.name = strategy_instance.metadata.display_name
        self.version = "1.5.0"
        self._symbol = ""

    def on_init(self, df):
        """Pre-calculate signals for the entire period"""
        try:
            self.signals_df = self.strategy_instance.generate_signals(df, self.params)
        except Exception as e:
            logger.error(f"Error in strategy generate_signals: {e}")
            self.signals_df = None

    def on_bar(self, bar, history, positions, executor):
        """Called for each bar - looks up pre-calculated signals"""
        if self.signals_df is None:
            return None
            
        timestamp = bar.name
        if self.signals_df is None or timestamp not in self.signals_df.index:
            return None
            
        row = self.signals_df.loc[timestamp]
        signal = row.get('signal')
        symbol = self._symbol or "UNKNOWN"

        if signal == 'BUY':
            if not executor.has_position(symbol):
                # Calculate quantity: use 95% of cash to be safe with costs
                price = bar['close']
                qty = int((executor.cash * 0.95) / price)
                if qty > 0:
                    executor.submit_order(
                        symbol=symbol,
                        side=OrderSide.BUY,
                        quantity=qty,
                        order_type=OrderType.MARKET
                    )
        elif signal == 'SELL':
            if executor.has_position(symbol):
                pos = executor.get_position(symbol)
                executor.submit_order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    quantity=pos.quantity,
                    order_type=OrderType.MARKET
                )
        return None

def get_strategy_class(name: str):
    """Get strategy class by name (Old System) or Adapter (New System)"""
    from strategies import AVAILABLE_STRATEGIES
    
    # Try old system first
    if name in AVAILABLE_STRATEGIES:
        return AVAILABLE_STRATEGIES[name]
    
    # Try new registry system
    new_strat = StrategyRegistry.get(name)
    if new_strat:
        # Return a lambda that creates the adapter
        return lambda params: NewStrategyAdapter(new_strat, params)
        
    if name not in AVAILABLE_STRATEGIES:
        available_old = list(AVAILABLE_STRATEGIES.keys())
        available_new = [s.name for s in StrategyRegistry.list_all()]
        available = ', '.join(available_old + available_new[:10]) + "..."
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {name}. Total available: {len(available_old) + len(available_new)}")
    
    return AVAILABLE_STRATEGIES[name]


async def load_data_for_symbol(symbol: str, start_date: date, end_date: date, db: Session) -> pd.DataFrame:
    """Load historical data from database"""
    from models_ml import Nifty100Daily
    from sqlalchemy import and_, select
    
    # Use select() for async session compatibility
    stmt = select(Nifty100Daily).where(
        and_(
            Nifty100Daily.symbol == symbol,
            Nifty100Daily.timestamp >= start_date,
            Nifty100Daily.timestamp <= end_date
        )
    ).order_by(Nifty100Daily.timestamp.asc())
    
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    if not records:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for {symbol} between {start_date} and {end_date}"
        )
    
    data = []
    for r in records:
        data.append({
            'date': r.timestamp,
            'open': r.open,
            'high': r.high,
            'low': r.low,
            'close': r.close,
            'volume': r.volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('date', inplace=True)
    df.index = pd.to_datetime(df.index)
    
    return df


# =====================
# API Endpoints
# =====================

@router.get("/strategies", response_model=StrategyListResponse)
async def list_strategies():
    """List available trading strategies"""
    try:
        from strategies import list_strategies as get_all_strategies
        strategies = get_all_strategies()
        return {"strategies": strategies}
    except Exception as e:
        logger.error(f"Error listing strategies: {e}")
        return {"strategies": [
            {"name": "MACrossover", "description": "Moving Average Crossover", "params": {"fast_period": 10, "slow_period": 30}},
            {"name": "RSIMeanReversion", "description": "RSI Mean Reversion", "params": {"period": 14, "oversold": 30, "overbought": 70}}
        ]}


@router.post("/backtest/run", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest, db: Session = Depends(get_db)):
    """
    Run a backtest for a strategy
    
    Returns performance metrics including:
    - Total return
    - Sharpe ratio
    - Max drawdown
    - Win rate
    - Number of trades
    """
    try:
        from core.backtest.engine import BacktestEngine, BacktestConfig
        
        logger.info(f"Running backtest: {request.strategy} on {request.symbol}")
        
        # Load data
        data = await load_data_for_symbol(
            request.symbol,
            request.start_date,
            request.end_date,
            db
        )
        
        # Get strategy class and create instance
        strategy_class = get_strategy_class(request.strategy)
        strategy = strategy_class(request.params)
        
        # If it's the new adapter system, set the symbol
        if isinstance(strategy, NewStrategyAdapter):
            strategy._symbol = request.symbol
        
        # Create backtest config
        config = BacktestConfig(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital
        )
        
        # Run backtest
        engine = BacktestEngine(config)
        engine.load_data(data)
        result = engine.run(strategy)
        
        return BacktestResponse(
            status="success",
            run_id=result.run_id,
            strategy=result.strategy_name,
            symbol=request.symbol,
            metrics=result.metrics.to_dict(),
            trade_count=len(result.trades),
            duration_seconds=result.duration_seconds
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


@router.post("/walkforward/run", response_model=WFAResponse)
async def run_walkforward(request: WFARequest, db: Session = Depends(get_db)):
    """
    Run walk-forward analysis
    
    Performs rolling window backtests to assess strategy robustness
    """
    try:
        from core.walkforward.wfa_engine import WalkForwardEngine, WFAConfig
        
        logger.info(f"Running WFA: {request.strategy} on {request.symbol}")
        
        # Load data
        data = await load_data_for_symbol(
            request.symbol,
            request.start_date,
            request.end_date,
            db
        )
        
        # Get strategy class
        strategy_class = get_strategy_class(request.strategy)
        
        # Create WFA config
        config = WFAConfig(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            train_days=request.train_days,
            test_days=request.test_days,
            initial_capital=request.initial_capital,
            optimize=request.optimize
        )
        
        # Run WFA
        engine = WalkForwardEngine(config)
        result = engine.run(
            strategy_class=strategy_class,
            strategy_params=request.params or {},
            data=data
        )
        
        return WFAResponse(
            status="success",
            strategy=result.strategy_name,
            symbol=request.symbol,
            num_windows=len(result.windows),
            total_test_return=result.total_test_return,
            test_return_pct=result.test_return_pct,
            avg_sharpe=result.avg_sharpe,
            robustness_ratio=result.robustness_ratio,
            consistency=result.consistency
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"WFA failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"WFA failed: {str(e)}")


@router.get("/symbols")
async def list_available_symbols(db: Session = Depends(get_db)):
    """Get list of Nifty 200 symbols with available data information"""
    from models_ml import Nifty100Daily
    from sqlalchemy import select, func
    import json
    from pathlib import Path
    
    try:
        # Load Nifty 200 symbols from JSON file
        json_path = Path(__file__).parent.parent / "nifty200_instruments.json"
        nifty200_symbols = []
        
        if json_path.exists():
            with open(json_path, 'r') as f:
                nifty200_data = json.load(f)
                nifty200_symbols = [item[0] for item in nifty200_data]  # Extract symbol names
        
        # Get database data availability for symbols
        db_data_info = {}
        try:
            stmt = select(
                Nifty100Daily.symbol,
                func.count(Nifty100Daily.id).label('bar_count'),
                func.min(Nifty100Daily.timestamp).label('start_date'),
                func.max(Nifty100Daily.timestamp).label('end_date')
            ).group_by(Nifty100Daily.symbol)
            
            result = await db.execute(stmt)
            results = result.all()
            
            for r in results:
                db_data_info[r.symbol] = {
                    "bar_count": r.bar_count,
                    "start_date": r.start_date.isoformat() if r.start_date else None,
                    "end_date": r.end_date.isoformat() if r.end_date else None
                }
        except Exception as e:
            logger.warning(f"Could not fetch DB data info: {e}")
        
        # Build response with all Nifty 200 symbols
        symbols = []
        for symbol in nifty200_symbols:
            symbol_info = {
                "symbol": symbol,
                "in_nifty200": True,
                "has_data": symbol in db_data_info,
                "bar_count": db_data_info.get(symbol, {}).get("bar_count", 0),
                "start_date": db_data_info.get(symbol, {}).get("start_date"),
                "end_date": db_data_info.get(symbol, {}).get("end_date")
            }
            symbols.append(symbol_info)
        
        # Sort alphabetically
        symbols.sort(key=lambda x: x["symbol"])
        
        return {
            "status": "success", 
            "symbols": symbols, 
            "count": len(symbols),
            "with_data_count": len([s for s in symbols if s["has_data"]])
        }
        
    except Exception as e:
        logger.error(f"Error listing symbols: {e}")
        # Return fallback list of common symbols
        fallback_symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", 
                           "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "ASIANPAINT", "BAJFINANCE",
                           "MARUTI", "TITAN", "WIPRO", "HCLTECH", "TATAMOTORS", "AXISBANK"]
        return {
            "status": "success",
            "symbols": [{"symbol": s, "in_nifty200": True, "has_data": True, "bar_count": 500} for s in fallback_symbols],
            "count": len(fallback_symbols),
            "with_data_count": len(fallback_symbols)
        }


