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
async def get_nifty100_top_movers(refresh: bool = False):
    """(Frontend Compat) Alias for default Top Movers."""
    try:
        from services.market_service import get_market_service
        return await get_market_service().get_nifty100_top_movers(bypass_cache=refresh)
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
async def get_top_movers(limit: int = 5, refresh: bool = False):
    """Get top gainers and losers from NIFTY 100."""
    return await market_service.get_nifty100_top_movers(limit, bypass_cache=refresh)

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


@router.get("/orchestrator/status")
async def get_orchestrator_status_alias(current_user: User = Depends(get_current_user)):
    """Alias for /orchestrator-status."""
    return await get_orchestrator_status(current_user)


@router.get("/health")
async def get_market_health():
    """Get market service health."""
    return {"status": "healthy", "service": "Market Data Service", "is_healthy": True}


@router.get("/health-report")
async def get_market_health_report(current_user: User = Depends(get_current_user)):
    """Comprehensive Market Data Health and Connectivity Monitor."""
    try:
        from services.market_data_orchestrator import get_market_data_orchestrator
        from services.dragonfly_client import get_cache
        from datetime import datetime
        import time
        
        orchestrator = get_market_data_orchestrator()
        cache = get_cache()
        
        # Test Cache latency
        start_cache = time.perf_counter()
        cache_available = cache.is_available()
        if cache_available:
            await cache.get_async("qai:health_ping")
        cache_latency = (time.perf_counter() - start_cache) * 1000
        
        status_info = orchestrator.get_status()
        
        return {
            "status": "healthy" if status_info.get("is_healthy") else "degraded",
            "timestamp": datetime.now().isoformat(),
            "websocket": {
                "active_source": status_info.get("source"),
                "is_running": orchestrator.is_running,
                "last_tick_time": status_info.get("last_tick"),
                "error_count": status_info.get("rest_error_count", 0)
            },
            "cache": {
                "available": cache_available,
                "latency_ms": round(cache_latency, 2),
                "tracked_symbols": status_info.get("symbol_count", 0)
            },
            "system_health": {
                "is_market_open": orchestrator.market_hours.is_market_open(),
                "trading_date": orchestrator.market_hours.get_trading_date()
            }
        }
    except Exception as e:
        logger.error(f"Health report endpoint failed: {e}")
        return {"status": "unhealthy", "error": str(e)}
