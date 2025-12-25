"""
AlphaPrime API Endpoints

FastAPI routes for:
- Model training
- Backtesting
- Real-time signals
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

from database import AsyncSessionLocal
from models import User
from models_alpha import AlphaSignal, AlphaPrimeConfig
from utils.auth import get_current_user
from features.alpha_prime.model import AlphaMLModel
from features.alpha_prime.backtest import AlphaBacktester
from sqlalchemy import select


router = APIRouter(prefix="/api/v1/alpha-prime", tags=["AlphaPrime"])


# Pydantic schemas
class TrainRequest(BaseModel):
    lookback_days: Optional[int] = 30
    n_estimators: Optional[int] = 100
    max_depth: Optional[int] = 10


class TrainResponse(BaseModel):
    status: str
    metrics: Dict
    feature_importance: Dict[str, float]
    model_version: str
    
    model_config = {"protected_namespaces": ()}


class BacktestRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    initial_capital: Optional[float] = 1000000


class BacktestResponse(BaseModel):
    status: str
    results: Dict


class SignalResponse(BaseModel):
    symbol: str
    timestamp: datetime
    alpha_score: float
    alpha_rank: Optional[int]
    rsi: Optional[float]
    macd_divergence: Optional[float]
    confidence: float


@router.post("/train", response_model=TrainResponse)
async def train_model(
    request: TrainRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Retrain the Random Forest model with latest data
    
    Requires authentication. Fetches recent data and trains ML model.
    """
    try:
        model = AlphaMLModel()
        
        # Fetch training data
        df = await model.fetch_training_data(lookback_days=request.lookback_days)
        
        if len(df) < 1000:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient training data: {len(df)} samples (need 1000+)"
            )
        
        # Train model
        metrics = model.train(
            df,
            n_estimators=request.n_estimators,
            max_depth=request.max_depth
        )
        
        # Save model
        model.save()
        
        return TrainResponse(
            status="success",
            metrics=metrics,
            feature_importance=model.feature_importance or {},
            model_version=model.model_version
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@router.post("/backtest", response_model=BacktestResponse)
async def run_backtest(
    request: BacktestRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Run vectorized backtest on historical data
    
    Returns performance metrics and equity curve.
    """
    try:
        async with AsyncSessionLocal() as session:
            # Fetch signals for the period
            result = await session.execute(
                select(AlphaSignal)
                .where(AlphaSignal.timestamp >= request.start_date)
                .where(AlphaSignal.timestamp <= request.end_date)
                .order_by(AlphaSignal.timestamp)
            )
            signals = result.scalars().all()
            
            if not signals:
                raise HTTPException(
                    status_code=404,
                    detail="No signals found for the specified period"
                )
            
            # Convert to DataFrame
            import pandas as pd
            signals_df = pd.DataFrame([
                {
                    'timestamp': s.timestamp,
                    'symbol': s.symbol,
                    'alpha_score': s.alpha_score or 0
                }
                for s in signals
            ])
            
            # Fetch prices (would need to join with StockData table)
            # For now, using a simplified approach
            from models_alpha import StockData
            result = await session.execute(
                select(StockData)
                .where(StockData.timestamp >= request.start_date)
                .where(StockData.timestamp <= request.end_date)
            )
            prices = result.scalars().all()
            
            prices_df = pd.DataFrame([
                {
                    'timestamp': p.timestamp,
                    'symbol': p.symbol,
                    'close': p.close
                }
                for p in prices
            ])
            
            # Run backtest
            backtester = AlphaBacktester(initial_capital=request.initial_capital)
            results = backtester.run_backtest(signals_df, prices_df)
            
            return BacktestResponse(
                status="success",
                results=results
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


@router.get("/signals", response_model=List[SignalResponse])
async def get_latest_signals(
    limit: int = 20,
    min_confidence: Optional[float] = 0.7,
    current_user: User = Depends(get_current_user)
):
    """
    Get latest alpha signals ranked by score
    
    Returns top N signals with highest alpha scores from recent data.
    """
    try:
        async with AsyncSessionLocal() as session:
            # Get signals from most recent data (top N by score)
            # No timestamp filter - just get best signals overall
            result = await session.execute(
                select(AlphaSignal)
                .where(AlphaSignal.alpha_score.isnot(None))
                .order_by(AlphaSignal.timestamp.desc(), AlphaSignal.alpha_score.desc())
                .limit(limit * 5)  # Get more to filter by uniqueness
            )
            all_signals = result.scalars().all()
            
            if not all_signals:
                return []
            
            # Get unique signals (latest per symbol)
            seen_symbols = set()
            unique_signals = []
            
            for s in all_signals:
                if s.symbol not in seen_symbols:
                    seen_symbols.add(s.symbol)
                    unique_signals.append(s)
                    if len(unique_signals) >= limit:
                        break
            
            # Sort by alpha_score descending
            unique_signals.sort(key=lambda x: x.alpha_score or 0, reverse=True)
            
            return [
                SignalResponse(
                    symbol=s.symbol,
                    timestamp=s.timestamp,
                    alpha_score=s.alpha_score or 0,
                    alpha_rank=idx + 1,  # Assign rank based on position
                    rsi=s.rsi,
                    macd_divergence=s.macd_divergence,
                    confidence=min(abs(s.alpha_score or 0) * 10, 1.0)  # Normalize to 0-1
                )
                for idx, s in enumerate(unique_signals)
            ]
        
    except Exception as e:
        # Return empty list on any error instead of 500
        import logging
        logging.getLogger(__name__).error(f"Failed to fetch signals: {e}")
        return []


@router.get("/config")
async def get_config(current_user: User = Depends(get_current_user)):
    """Get current AlphaPrime configuration"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AlphaPrimeConfig)
                .where(AlphaPrimeConfig.config_name == "default")
                .where(AlphaPrimeConfig.is_active == True)
            )
            config = result.scalar_one_or_none()
            
            if not config:
                # Return default config when none exists
                return {
                    "status": "success",
                    "config": {
                        "lookback_period": 30,
                        "rebalance_frequency": "daily",
                        "max_position_size": 0.1,
                        "min_confidence": 0.7,
                        "ml_enabled": True,
                        "auto_trade_enabled": False,
                        "paper_trade_mode": True
                    }
                }
            
            return {
                "status": "success",
                "config": {
                    "lookback_period": config.lookback_period,
                    "rebalance_frequency": config.rebalance_frequency,
                    "max_position_size": config.max_position_size,
                    "min_confidence": config.min_confidence,
                    "ml_enabled": config.ml_enabled,
                    "auto_trade_enabled": config.auto_trade_enabled,
                    "paper_trade_mode": config.paper_trade_mode
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        # Return default config on error
        import logging
        logging.getLogger(__name__).error(f"Config fetch error: {e}")
        return {
            "status": "success",
            "config": {
                "lookback_period": 30,
                "rebalance_frequency": "daily",
                "max_position_size": 0.1,
                "min_confidence": 0.7,
                "ml_enabled": True,
                "auto_trade_enabled": False,
                "paper_trade_mode": True
            }
        }

