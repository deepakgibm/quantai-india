"""
APF - ML Forecast API Endpoint
FastAPI router for Adaptive Price Forecast predictions
"""

import logging
from fastapi import APIRouter, HTTPException, Query

from ml.predictor import get_apf_predictor
from ml.schemas import ForecastResponse
from models import User
from utils.auth import get_current_user
from fastapi import Depends

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/ml",
    tags=["ML Forecast"]
)


@router.get("/predict", response_model=ForecastResponse)
async def predict_price(
    symbol: str = Query(..., min_length=1, description="Stock symbol (e.g., RELIANCE)"),
    timeframe: str = Query(default="5m", description="Candle timeframe: 5m, 15m, 1h, 1d"),
    horizon: int = Query(default=10, ge=1, le=50, description="Number of future candles to predict"),
    current_user: User = Depends(get_current_user)
):
    """
    Generate Adaptive Price Forecast for a stock.
    
    Returns:
        - Historical actual prices
        - Predicted future prices
        - Upper and lower confidence bands
        - Model confidence score
    
    Note: Predictions are statistical forecasts and should not be used as investment advice.
    """
    logger.info(f"APF Prediction request: symbol={symbol}, timeframe={timeframe}, horizon={horizon}")
    
    try:
        predictor = get_apf_predictor()
        result = await predictor.predict(
            symbol=symbol.upper(),
            timeframe=timeframe,
            horizon=horizon
        )
        
        logger.info(f"APF Prediction successful: {symbol}, confidence={result.confidence}")
        return result
        
    except ValueError as e:
        logger.warning(f"APF Prediction failed (data issue): {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "insufficient_data",
                "message": str(e),
                "symbol": symbol,
                "data_available": False
            }
        )
    except RuntimeError as e:
        logger.error(f"APF Prediction failed (model issue): {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "model_not_ready",
                "message": str(e),
                "symbol": symbol,
                "data_available": True
            }
        )
    except Exception as e:
        logger.error(f"APF Prediction failed (unexpected): {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "prediction_failed",
                "message": str(e),
                "symbol": symbol
            }
        )


@router.get("/status")
async def get_status(current_user: User = Depends(get_current_user)):
    """
    Get APF model status and availability.
    """
    return {
        "status": "available",
        "model_version": "apf_v1",
        "supported_timeframes": ["5m", "15m", "1h", "1d"],
        "max_horizon": 50,
        "xgboost_available": True  # Will be checked at runtime
    }


@router.get("/symbols")
async def get_available_symbols(current_user: User = Depends(get_current_user)):
    """
    Get list of symbols with trained models.
    """
    from pathlib import Path
    
    model_dir = Path(__file__).parent.parent.parent / "ml" / "models"
    
    if not model_dir.exists():
        return {"symbols": [], "note": "No trained models yet. Run trainer first."}
    
    models = list(model_dir.glob("apf_*.joblib"))
    symbols = set()
    
    for model_path in models:
        # Parse: apf_SYMBOL_TIMEFRAME.joblib
        parts = model_path.stem.split("_")
        if len(parts) >= 2:
            symbols.add(parts[1])
    
    return {
        "symbols": sorted(list(symbols)),
        "total_models": len(models)
    }
