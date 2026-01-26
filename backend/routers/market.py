from fastapi import APIRouter, Depends
from datetime import datetime
from models import User
from utils.auth import get_current_user
import logging

from services.market_service import get_market_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Market"])
market_service = get_market_service()

@router.get("/nifty100/top-movers")
@router.get("/top-movers")
async def get_nifty100_top_movers(limit: int = 5):
    return await market_service.get_nifty100_top_movers(limit)

@router.get("/global-context")
async def get_global_market_context():
    return await market_service.get_global_market_context()

@router.get("/nifty100/status")
@router.get("/status")
async def get_market_status():
    # Dynamic status from ranking service
    from services.nifty100_ranking_service import get_nifty100_ranking_service
    service = get_nifty100_ranking_service()
    rankings = await service.get_rankings()
    return {
        "status": "active" if rankings.get("source") == "websocket" else "stale",
        "last_update": rankings.get("timestamp")
    }

@router.get("/market-indices")
async def get_market_indices():
    from services.trading_service import get_trading_service
    return await get_trading_service().get_market_indices()

@router.get("/orchestrator-status")
async def get_orchestrator_status():
    from services.market_data_orchestrator import get_market_data_orchestrator
    orchestrator = get_market_data_orchestrator()
    return orchestrator.get_status()

@router.get("/health")
async def get_market_health():
    return {"status": "healthy", "service": "market-data"}

@router.get("/heatmap")
async def get_sector_heatmap(current_user: User = Depends(get_current_user)):
    return await market_service.get_sector_performance()

@router.get("/sector/{sector_name}")
async def get_sector_stocks(sector_name: str, current_user: User = Depends(get_current_user)):
    return await market_service.get_sector_stocks(sector_name)
