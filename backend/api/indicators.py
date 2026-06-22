from fastapi import APIRouter, Depends
from models import User
from utils.auth import get_current_user
from services.dragonfly_client import get_cache, CacheKeys
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Indicators"])

@router.get("/heatmap")
async def get_heatmap_sectors(current_user: User = Depends(get_current_user)):
    """Get aggregated sector performance heatmap."""
    from utils.market_state import is_market_open, get_trading_date
    cache = get_cache()
    
    if not is_market_open():
        date_str = get_trading_date().strftime("%Y-%m-%d")
        snapshot = cache.get(f"snapshot:heatmap_sectors:{date_str}")
        if snapshot:
            return {"status": "success", "data": snapshot.get("sectors", []), "source": "EOD_SNAPSHOT"}
    
    data = cache.get(CacheKeys.heatmap_all()) or []
    return {"status": "success", "data": data, "source": "CACHE"}

@router.get("/sector/{sector_name}")
async def get_sector_stocks(sector_name: str, current_user: User = Depends(get_current_user)):
    """Get component stocks for a sector with performance metrics."""
    from utils.market_state import is_market_open, get_trading_date
    cache = get_cache()
    
    if not is_market_open():
        date_str = get_trading_date().strftime("%Y-%m-%d")
        sector_key = sector_name.replace(" ", "_").lower()
        snapshot = cache.get(f"snapshot:heatmap_sector_{sector_key}:{date_str}")
        if snapshot:
            return {"status": "success", "stocks": snapshot.get("stocks", []), "source": "EOD_SNAPSHOT"}

    stocks = cache.get(f"{CacheKeys.sector_snapshot(sector_name)}:stocks") or []
    return {"status": "success", "stocks": stocks, "source": "CACHE"}
