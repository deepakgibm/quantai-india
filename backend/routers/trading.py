from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from database import get_db
from models import User
from schemas import DashboardStats, MarketIndex, InstrumentsListResponse, TopMover, GainersLosersResponse
from utils.auth import get_current_user
from services.trading_service import get_trading_service

logger = logging.getLogger(__name__)
router = APIRouter()
trading_service = get_trading_service()

@router.get("/dashboard", response_model=DashboardStats)
@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await trading_service.get_dashboard_stats(current_user, db)

@router.get("/health")
def get_health():
    return {"status": "healthy", "service": "quantai-trading-api"}

@router.get("/market-indices", response_model=List[MarketIndex])
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

@router.get("/top-gainers", response_model=List[TopMover])
async def get_top_gainers(current_user: User = Depends(get_current_user)):
    return await trading_service.get_top_gainers()

@router.get("/gainers-losers", response_model=List[GainersLosersResponse])
async def get_gainers_losers(current_user: User = Depends(get_current_user)):
    # This specific combined format is still unique to the legacy router
    # but we can eventually move it to a ranking aggregator service
    from services.nifty100_ranking_service import get_nifty100_ranking_service
    service = get_nifty100_ranking_service()
    rankings = await service.get_rankings()
    
    combined = []
    for g in rankings.get('gainers', [])[:3]:
        combined.append({"ticker": g['symbol'], "change": g['change_pct'], "color": "bg-green-500", "price": g['ltp']})
    for l in rankings.get('losers', [])[:3]:
        combined.append({"ticker": l['symbol'], "change": l['change_pct'], "color": "bg-red-500", "price": l['ltp']})
    return combined
