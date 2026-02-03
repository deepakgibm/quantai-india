"""
Unified Forecast API Router
Provides inference-only price predictions from multiple algorithms.
"""

import logging
import time
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from datetime import datetime

from models import User
from utils.auth import get_current_user
from ml.schemas import (
    AlgorithmListResponse,
    ForecastRunRequest,
    ForecastRunResponse,
    ForecastResponse
)
from ml.algorithm_registry import get_algorithm_registry
from database import get_db
from services.dragonfly_client import get_cache

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI Forecast"])

@router.get("/algorithms", response_model=AlgorithmListResponse)
async def list_algorithms(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List available forecasting models and their status."""
    registry = get_algorithm_registry()
    algorithms = await registry.list_all(db=db, symbol=symbol, timeframe=timeframe)
    return AlgorithmListResponse(algorithms=algorithms, count=len(algorithms))

@router.post("/run", response_model=ForecastRunResponse)
async def run_forecast(
    request: ForecastRunRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Run a price forecast using the selected algorithm.
    Target: <200ms using Result-Level Caching.
    """
    start_time = time.time()
    cache_key = f"qai:fc:{request.symbol}:{request.timeframe}:{request.algorithm_id}"
    cache = get_cache()
    
    # 1. Result-Level Cache Check
    if cache.is_available():
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info(f"Forecast Cache Hit: {cache_key}")
            return cached_result

    # 2. PRO Access Control (Temporarily Disabled for Debugging/Demo)
    registry = get_algorithm_registry()
    algo = registry.get(request.algorithm_id)
    # if algo and algo.metadata.is_pro and getattr(current_user, "subscription_level", "FREE") != "PRO":
    #     raise HTTPException(status_code=403, detail="PRO subscription required for this model")

    # 3. Execution (Inference-Only)
    try:
        # Fetching data (will be optimized to Hot Cache in later steps)
        import pandas as pd
        df = await _fetch_from_database(request.symbol, request.timeframe)
        
        if df is None or len(df) < 30:
            raise HTTPException(status_code=400, detail="Insufficient historical data")

        # Force inference-only mode (model.train() is NOT called here)
        result = await registry.run_forecast(
            algorithm_id=request.algorithm_id,
            df=df,
            symbol=request.symbol,
            exchange=request.exchange,
            timeframe=request.timeframe,
            horizon=request.horizon,
            confidence_level=request.confidence_level,
            include_confidence_bands=request.include_confidence_bands
        )
        
        # 4. Cache the result (TTL = remaining candle duration or 5m)
        if cache.is_available():
            cache.set(cache_key, result, ttl=300)
            
        return result
        
    except Exception as e:
        logger.error(f"Forecast failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/predict", response_model=ForecastResponse)
async def predict_apf(
    symbol: str = Query(..., description="Stock symbol"),
    timeframe: str = Query(default="15m"),
    horizon: int = Query(default=10, le=50),
    current_user: User = Depends(get_current_user)
):
    """Legacy Adaptive Price Forecast (APF) compatibility endpoint."""
    try:
        from ml.predictor import get_apf_predictor
        predictor = get_apf_predictor()
        return await predictor.predict(symbol=symbol.upper(), timeframe=timeframe, horizon=horizon)
    except Exception as e:
        logger.error(f"APF Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _fetch_from_database(symbol: str, timeframe: str, limit: int = 200):
    """Internal helper to fetch data from database."""
    try:
        from models_alpha import StockCandle, InstrumentMaster, TimeframeMapper
        from sqlalchemy import select, desc
        import pandas as pd
        
        tf_minutes = TimeframeMapper.to_minutes(timeframe)
        
        async for db in get_db():
            stmt = (
                select(StockCandle)
                .join(InstrumentMaster, StockCandle.instrument_id == InstrumentMaster.instrument_id)
                .where(InstrumentMaster.symbol == symbol)
                .where(StockCandle.timeframe == tf_minutes)
                .order_by(desc(StockCandle.candle_ts))
                .limit(limit)
            )
            
            result = await db.execute(stmt)
            records = result.scalars().all()
            
            if not records: return None
            
            data = [{
                'timestamp': r.candle_ts,
                'open': float(r.open), 'high': float(r.high),
                'low': float(r.low), 'close': float(r.close),
                'volume': int(r.volume)
            } for r in records]
            
            df = pd.DataFrame(data).sort_values('timestamp').reset_index(drop=True)
            df.set_index('timestamp', inplace=True)
            return df
    except Exception as e:
        logger.error(f"DB Fetch error: {e}")
        return None
