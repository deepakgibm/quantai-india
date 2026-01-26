from fastapi import APIRouter, Depends
from typing import List, Dict, Any

from models import User
from utils.auth import get_current_user
from services.market_service import get_market_service

router = APIRouter(prefix="/market", tags=["Market (v1)"])
market_service = get_market_service()

@router.get("/nifty100/top-movers")
async def get_nifty100_top_movers(limit: int = 5):
    return await market_service.get_nifty100_top_movers(limit)

@router.get("/global-context")
async def get_global_market_context():
    return await market_service.get_global_market_context()

@router.get("/heatmap")
async def get_sector_heatmap(current_user: User = Depends(get_current_user)):
    return await market_service.get_sector_performance()

@router.get("/sector/{sector_name}")
async def get_sector_stocks(sector_name: str, current_user: User = Depends(get_current_user)):
    return await market_service.get_sector_stocks(sector_name)
