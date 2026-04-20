from fastapi import APIRouter, Depends
from models import User
from utils.auth import get_current_user
import logging

from services.market_service import get_market_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Market Data"])
market_service = get_market_service()

@router.get("/orchestrator-status")
async def get_orchestrator_status(current_user: User = Depends(get_current_user)):
    """Get internal status of the Market Data Orchestrator."""
    try:
        from services.market_data_orchestrator import get_market_data_orchestrator
        orchestrator = get_market_data_orchestrator()
        return orchestrator.get_status()
    except Exception as e:
        logger.error(f"Orchestrator status check failed: {e}")
        return {"error": str(e), "is_healthy": False}

@router.get("/status")
async def get_market_status():
    """Get overall market status (Active/Stale/Closed)."""
    try:
        from services.nifty100_ranking_service import get_nifty100_ranking_service
        service = get_nifty100_ranking_service()
        rankings = await service.get_rankings()
        return {
            "status": "active" if rankings.get("source") == "websocket" else "stale",
            "last_update": rankings.get("timestamp")
        }
    except Exception as e:
        logger.error(f"Market status check failed: {e}")
        return {"status": "unknown"}

@router.get("/nifty100/top-movers")
async def get_nifty100_top_movers():
    """(Frontend Compat) Alias for default Top Movers."""
    try:
        from services.market_service import get_market_service
        return await get_market_service().get_nifty100_top_movers()
    except Exception as e:
        logger.error(f"Top movers fetch failed: {e}")
        return {
            "status": "error",
            "timestamp": None,
            "gainers": [],
            "losers": [],
            "source": "unavailable",
            "error": str(e)
        }

@router.get("/top-movers")
async def get_top_movers(limit: int = 5):
    """Get top gainers and losers from NIFTY 100."""
    return await market_service.get_nifty100_top_movers(limit)

@router.get("/global-context")
async def get_global_context():
    """Get global market sentiment and context."""
    return await market_service.get_global_market_context()

@router.get("/heatmap")
async def get_sector_heatmap(current_user: User = Depends(get_current_user)):
    """Get sector performance heatmap."""
    return await market_service.get_sector_performance()

@router.get("/sector/{sector_name}")
async def get_sector_stocks(sector_name: str, current_user: User = Depends(get_current_user)):
    """Get list of stocks within a specific sector."""
    return await market_service.get_sector_stocks(sector_name)

@router.get("/indices")
async def get_market_indices():
    """Get current levels of major market indices."""
    from services.trading_service import get_trading_service
    return await get_trading_service().get_market_indices()
