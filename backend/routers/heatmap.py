from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from models import User
from utils.auth import get_current_user
from services.dragonfly_client import CacheManager, CacheKeys

router = APIRouter()
print("DEBUG: Loading Heatmap Router MODULE")
cache = CacheManager()

@router.get("/sectors")
async def get_heatmap_sectors(current_user: User = Depends(get_current_user)):
    """
    Get aggregated sector heatmap data.
    
    During market hours: Returns live cache data
    After market hours: Returns EOD snapshot
    Source: Dragonfly/Redis/In-Memory Cache (qai:heatmap:all)
    Latency: <50ms
    """
    from utils.market_state import is_market_open, get_trading_date
    from services.memcached_client import get_cache as get_df_cache
    
    # Check if market is closed - return EOD snapshot
    if not is_market_open():
        df_cache = get_df_cache()
        date_str = get_trading_date().strftime("%Y-%m-%d")
        snapshot = df_cache.get(f"snapshot:heatmap_sectors:{date_str}")
        
        if snapshot and snapshot.get("sectors"):
            print(f"Heatmap GET /sectors: Returning EOD snapshot for {date_str}")
            return {
                "status": "success", 
                "data": snapshot["sectors"],
                "source": "EOD_SNAPSHOT",
                "trade_date": date_str,
                "market_status": "CLOSED"
            }
    
    # Market is open - use live data
    # 1. Fetch from Cache
    data = cache.get(CacheKeys.heatmap_all())
    print(f"Heatmap GET /sectors: Found {len(data) if data else 0} items. Key: {CacheKeys.heatmap_all()}")
    
    # 2. Return or Fallback
    if not data:
        return {"status": "success", "data": []}
    
    return {"status": "success", "data": data}

@router.get("/sector/{sector_name}")
async def get_sector_stocks(sector_name: str, current_user: User = Depends(get_current_user)):
    """
    Get all stocks for a specific sector.
    
    During market hours: Returns live cache data
    After market hours: Returns EOD snapshot for sector
    Source: Dragonfly/Redis/In-Memory Cache (qai:sector:{name}:stocks)
    """
    from utils.market_state import is_market_open, get_trading_date
    from services.memcached_client import get_cache as get_df_cache
    
    # Check if market is closed - return EOD snapshot
    if not is_market_open():
        df_cache = get_df_cache()
        date_str = get_trading_date().strftime("%Y-%m-%d")
        sector_key = sector_name.replace(" ", "_").lower()
        snapshot = df_cache.get(f"snapshot:heatmap_sector_{sector_key}:{date_str}")
        
        if snapshot:
            # Sort by change
            stocks = snapshot.get("top_stocks", []) + snapshot.get("bottom_stocks", [])
            stocks.sort(key=lambda x: x.get("change_percent", 0), reverse=True)
            return {
                "status": "success", 
                "stocks": stocks,
                "source": "EOD_SNAPSHOT",
                "trade_date": date_str,
                "market_status": "CLOSED"
            }
    
    # Market is open - use live data
    key = f"{CacheKeys.sector_snapshot(sector_name)}:stocks"
    
    # 2. Fetch
    stocks = cache.get(key)
    
    if not stocks:
        return {"status": "success", "stocks": []}
    
    # Sort by % change desc (User Req)
    try:
        stocks.sort(key=lambda x: x.get("change_pct", 0) or 0, reverse=True)
    except Exception:
        pass
        
    return {"status": "success", "stocks": stocks}

@router.post("/seed")
async def seed_data(current_user: User = Depends(get_current_user)):
    """Force-seed dummy data for demo purposes (RESTRICTED)."""
    # Security: Only allow specific admin or disable in production
    if current_user.email != "admin@quantai.in":
        raise HTTPException(status_code=403, detail="Only admins can seed data")
    
    # ... rest of the code ...

    import random
    sectors = ["Financial Services", "Energy", "IT", "Auto", "Pharma"]
    
    # 1. Create Dummy Stocks
    dummy_stocks = []
    symbol_map = {}
    
    for i in range(50):
        sec = random.choice(sectors)
        sym = f"STOCK-{i}"
        pct = random.uniform(-3.0, 3.0)
        stock = {
            "symbol": sym, 
            "ltp": random.uniform(100, 3000),
            "change_pct": round(pct, 2),
            "volume": random.randint(1000, 1000000),
            "sector": sec,
            "company_name": f"Dummy {sym} Ltd."
        }
        dummy_stocks.append(stock)
        
        # Cache Stock List for Drill Down (Group by Sector)
        key = f"{CacheKeys.sector_snapshot(sec)}:stocks"
        current_list = cache.get(key) or []
        current_list.append(stock)
        cache.set(key, current_list, ttl=300)

    # 2. Aggregation Logic (Mini version of worker)
    sector_snapshots = []
    for sec in sectors:
        # Get stocks for this sector (we just populated them in loop above, but let's re-filter dummy_stocks)
        sec_stocks = [s for s in dummy_stocks if s["sector"] == sec]
        if not sec_stocks: continue
        
        avg_pct = sum(s["change_pct"] for s in sec_stocks) / len(sec_stocks)
        snapshot = {
            "sector": sec,
            "avg_pct_change": round(avg_pct, 2),
            "bucket": "BULLISH" if avg_pct > 0.5 else "BEARISH" if avg_pct < -0.5 else "NEUTRAL",
            "advancers": sum(1 for s in sec_stocks if s["change_pct"] > 0),
            "decliners": sum(1 for s in sec_stocks if s["change_pct"] < 0),
            "stock_count": len(sec_stocks)
        }
        sector_snapshots.append(snapshot)
        cache.set(CacheKeys.sector_snapshot(sec), snapshot, ttl=300)
    
    # 2. Aggregation Logic (Mini version of worker)
    # ... (Keep existing logic)
    
    # 3. Write All Heatmap (Direct Write)
    cache.set(CacheKeys.heatmap_all(), sector_snapshots, ttl=300)
    
    # 4. Write Source (all_snapshots) so Worker maintains it
    cache.set(CacheKeys.all_snapshots(), dummy_stocks, ttl=300)
    print(f"Heatmap SEEDED: {len(sector_snapshots)} sectors. Source: {len(dummy_stocks)} stocks.")
    
    return {"status": "seeded", "sectors": len(sector_snapshots), "stocks": len(dummy_stocks)}
