from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from schemas import DashboardStats, MarketIndex, InstrumentsListResponse
from utils.auth import get_current_user
from services.trading_service import get_trading_service

router = APIRouter(prefix="/trading", tags=["Trading (v1)"])
trading_service = get_trading_service()

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await trading_service.get_dashboard_stats(current_user, db)

@router.get("/indices", response_model=List[MarketIndex])
async def get_market_indices():
    return await trading_service.get_market_indices()

@router.get("/instruments", response_model=InstrumentsListResponse)
async def get_instruments():
    instruments = await trading_service.get_instruments()
    return {
        "status": "success",
        "instruments": instruments,
        "count": len(instruments)
    }
