from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from models import User
from utils.auth import get_current_user
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models_alpha import InstrumentMaster
from experiment_lab.registry import STRATEGY_CATALOG
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Experiment Lab"])

@router.get("/strategies")
async def get_lab_strategies(current_user: User = Depends(get_current_user)):
    """Get all 70 experiment lab strategies."""
    return {
        "status": "success",
        "strategies": STRATEGY_CATALOG,
        "total_count": len(STRATEGY_CATALOG)
    }

@router.get("/symbols")
async def get_lab_symbols(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all available symbols in the experiment lab."""
    try:
        stmt = select(InstrumentMaster.symbol).where(InstrumentMaster.is_active == True).distinct()
        res = await db.execute(stmt)
        symbols = list(res.scalars().all())
        if not symbols:
            # Fallback Nifty 50 symbols
            symbols = [
                "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", 
                "SBIN", "BHARTIARTL", "ITC", "LTIM", "HINDUNILVR",
                "AXISBANK", "LT", "BAJFINANCE", "KOTAKBANK", "MARUTI"
            ]
        return {
            "status": "success",
            "symbols": sorted(symbols),
            "count": len(symbols)
        }
    except Exception as e:
        logger.warning(f"Failed to fetch symbols from DB: {e}")
        # Graceful fallback
        return {
            "status": "success",
            "symbols": [
                "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", 
                "SBIN", "BHARTIARTL", "ITC", "LTIM", "HINDUNILVR"
            ],
            "count": 10
        }
