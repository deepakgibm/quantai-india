"""
Forecast API Router
Enterprise-grade forecast endpoints with algorithm selection.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import pandas as pd

from models import User
from utils.auth import get_current_user
from ml.schemas import (
    AlgorithmInfo,
    AlgorithmListResponse,
    ForecastRunRequest,
    ForecastRunResponse
)
from ml.algorithm_registry import get_algorithm_registry

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/forecast",
    tags=["Forecast"]
)


@router.get("/algorithms", response_model=AlgorithmListResponse)
async def list_algorithms(
    current_user: User = Depends(get_current_user)
):
    """
    List all available forecast algorithms.
    
    Returns metadata for each algorithm including:
    - id, name, version
    - type (ensemble, ml, dl, statistical)
    - recommended flag
    - supported timeframes and max horizon
    - description and features
    """
    registry = get_algorithm_registry()
    algorithms = registry.list_all()
    
    return AlgorithmListResponse(
        algorithms=algorithms,
        count=len(algorithms)
    )


@router.post("/run", response_model=ForecastRunResponse)
async def run_forecast(
    request: ForecastRunRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Run a price forecast using the selected algorithm.
    
    Request body:
    - symbol: Stock symbol (e.g., RELIANCE)
    - exchange: Stock exchange (default: NSE)
    - timeframe: Candle timeframe (1m, 5m, 15m, 30m, 1h, 1d)
    - horizon: Number of candles to predict (5-50)
    - algorithm_id: Algorithm to use
    - confidence_level: Confidence interval level (0.68 or 0.95)
    - include_confidence_bands: Whether to include bands
    
    Returns:
    - request_id: Unique request identifier
    - forecast: Array of predicted candles
    - confidence_bands: Upper/lower band arrays
    - metrics: Model confidence, predicted move %, volatility, latency
    """
    logger.info(
        f"Forecast request: symbol={request.symbol}, "
        f"algorithm={request.algorithm_id}, horizon={request.horizon}"
    )
    
    try:
        # Fetch historical data
        df = await _fetch_historical_data(
            symbol=request.symbol,
            exchange=request.exchange,
            timeframe=request.timeframe
        )
        
        if df is None or len(df) < 30:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "insufficient_data",
                    "message": f"Not enough historical data for {request.symbol}",
                    "symbol": request.symbol,
                    "data_available": False
                }
            )
        
        # Run forecast
        registry = get_algorithm_registry()
        result = registry.run_forecast(
            algorithm_id=request.algorithm_id,
            df=df,
            symbol=request.symbol,
            exchange=request.exchange,
            timeframe=request.timeframe,
            horizon=request.horizon,
            confidence_level=request.confidence_level,
            include_confidence_bands=request.include_confidence_bands
        )
        
        logger.info(
            f"Forecast completed: {request.symbol}, "
            f"latency={result.metrics.model_latency_ms}ms"
        )
        return result
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Forecast validation error: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "validation_error",
                "message": str(e),
                "symbol": request.symbol
            }
        )
    except RuntimeError as e:
        logger.error(f"Forecast runtime error: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "forecast_failed",
                "message": str(e),
                "symbol": request.symbol
            }
        )
    except Exception as e:
        logger.error(f"Unexpected forecast error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred",
                "symbol": request.symbol
            }
        )


@router.get("/status/{request_id}")
async def get_forecast_status(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get status of a forecast request (for async execution).
    
    Currently all forecasts are synchronous, so this returns
    a completed status if the request_id is recognized.
    
    TODO: Implement async forecast execution with task queue.
    """
    # Placeholder - async execution not yet implemented
    return {
        "request_id": request_id,
        "status": "completed",
        "message": "Async forecasting not yet implemented. All requests are synchronous."
    }


async def _fetch_historical_data(
    symbol: str,
    exchange: str,
    timeframe: str,
    lookback_candles: int = 200
) -> Optional[pd.DataFrame]:
    """
    Fetch historical OHLCV data for a symbol.
    
    Uses existing data fetcher with WebSocket -> REST -> DB fallback.
    """
    try:
        # Import data fetcher
        from services.data_fetcher import UnifiedDataFetcher
        
        fetcher = UnifiedDataFetcher()
        df, data_source = await fetcher.fetch(
            symbol=symbol,
            timeframe=timeframe,
            limit=lookback_candles
        )
        
        if df is not None and len(df) > 0:
            # Ensure required columns exist
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if all(col in df.columns for col in required_cols):
                return df
        
        return None
        
    except ImportError:
        # Fallback: try database directly
        logger.warning("UnifiedDataFetcher not available, trying database fallback")
        return await _fetch_from_database(symbol, timeframe, lookback_candles)
    except Exception as e:
        logger.error(f"Data fetch error for {symbol}: {e}")
        return await _fetch_from_database(symbol, timeframe, lookback_candles)


async def _fetch_from_database(
    symbol: str,
    timeframe: str,
    limit: int = 200
) -> Optional[pd.DataFrame]:
    """
    Fallback: Fetch data directly from database.
    """
    try:
        from database import get_db
        from models_ml import Nifty100Daily
        from sqlalchemy import select, desc
        from sqlalchemy.ext.asyncio import AsyncSession
        
        # Get database session
        async for db in get_db():
            # Query based on timeframe
            if timeframe in ['1d', 'D']:
                stmt = (
                    select(Nifty100Daily)
                    .where(Nifty100Daily.symbol == symbol)
                    .order_by(desc(Nifty100Daily.timestamp))
                    .limit(limit)
                )
                
                result = await db.execute(stmt)
                records = result.scalars().all()
                
                if not records:
                    return None
                
                # Convert to DataFrame
                data = []
                for r in records:
                    data.append({
                        'timestamp': r.timestamp,
                        'open': r.open,
                        'high': r.high,
                        'low': r.low,
                        'close': r.close,
                        'volume': r.volume
                    })
                
                df = pd.DataFrame(data)
                df = df.sort_values('timestamp').reset_index(drop=True)
                df.set_index('timestamp', inplace=True)
                return df
            else:
                # For intraday, try Nifty100Intraday if available
                try:
                    from models_ml import Nifty100Intraday
                    stmt = (
                        select(Nifty100Intraday)
                        .where(Nifty100Intraday.symbol == symbol)
                        .order_by(desc(Nifty100Intraday.timestamp))
                        .limit(limit)
                    )
                    
                    result = await db.execute(stmt)
                    records = result.scalars().all()
                    
                    if records:
                        data = [{
                            'timestamp': r.timestamp,
                            'open': r.open,
                            'high': r.high,
                            'low': r.low,
                            'close': r.close,
                            'volume': r.volume
                        } for r in records]
                        
                        df = pd.DataFrame(data)
                        df = df.sort_values('timestamp').reset_index(drop=True)
                        df.set_index('timestamp', inplace=True)
                        return df
                except ImportError:
                    pass
                
                # Fallback to daily data
                return await _fetch_from_database(symbol, '1d', limit)
                
    except Exception as e:
        logger.error(f"Database fetch error for {symbol}: {e}")
        return None
