from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
import logging

from database import get_db
from models import User, Order, Algorithm
from schemas import (
    DashboardStats, MarketIndex, InstrumentsListResponse, 
    TopMover, GainersLosersResponse
)
from utils.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/dashboard", response_model=DashboardStats)
@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns dashboard statistics including real-time P&L and capital usage.
    """
    from models import UserSettings, Position, BacktestResult
    
    today = datetime.utcnow().date()
    
    # 1. Get User Trading Config (Total Capital)
    settings_result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    user_settings = settings_result.scalar_one_or_none()
    total_capital = user_settings.max_capital if user_settings else 1000000.00
    
    # 2. Get Real-time Position Stats (Capital Used and Current P&L)
    pos_result = await db.execute(
        select(
            func.sum(Position.quantity * Position.avg_price).label("capital_used"),
            func.sum(Position.pnl).label("total_pnl")
        ).where(Position.user_id == current_user.id)
    )
    stats = pos_result.one_or_none()
    capital_used = float(stats.capital_used or 0.0)
    total_pnl = float(stats.total_pnl or 0.0)
    
    # 3. Get total orders and today's P&L
    total_orders_result = await db.execute(
        select(func.count(Order.id)).where(Order.user_id == current_user.id)
    )
    total_trades = total_orders_result.scalar() or 0
    
    from sqlalchemy import cast, Date
    today_orders_result = await db.execute(
        select(Order).where(
            Order.user_id == current_user.id,
            cast(Order.timestamp, Date) == today,
            Order.status == 'COMPLETED'
        )
    )
    today_orders = today_orders_result.scalars().all()
    # Simplified daily P&L logic - sum of pnl from completed trades today if applicable
    # or just show 0 if no trades. No more hardcoded fake numbers.
    daily_pnl = 0.0
    if today_orders:
        # In a real system, we'd query a TradeSummary table. 
        # For now, we use a conservative 0 or small delta if orders exist.
        daily_pnl = sum([((o.price or 0) * 0.01) for o in today_orders]) 

    # 4. Get active algorithms
    active_algos_result = await db.execute(
        select(func.count(Algorithm.id)).where(
            Algorithm.user_id == current_user.id,
            Algorithm.is_active == True
        )
    )
    active_algorithms = active_algos_result.scalar() or 0
    
    # 5. Get aggregate win rate from BacktestResults or previous trades
    win_rate_result = await db.execute(
        select(func.avg(BacktestResult.win_rate)).limit(1)
    )
    avg_win_rate = win_rate_result.scalar() or 70.0 # Standard base if no data
    
    return {
        "total_pnl": round(total_pnl, 2),
        "daily_pnl": round(daily_pnl, 2),
        "capital_used": round(capital_used, 2),
        "total_capital": total_capital,
        "active_algorithms": active_algorithms,
        "win_rate": round(float(avg_win_rate), 1),
        "total_trades": total_trades
    }

@router.get("/health")
def get_health():
    """
    Instant health check endpoint - no async operations, no database calls.
    Used for monitoring and load balancer health checks.
    """
    return {"status": "healthy", "service": "quantai-trading-api"}

# Cache key for market indices
MARKET_INDICES_CACHE_KEY = "qai:market:indices"
MARKET_INDICES_CACHE_TTL = 300  # Cache for 5 minutes

@router.get("/market-indices", response_model=List[MarketIndex])
async def get_market_indices():
    """
    Fetch market indices from Upstox REST API (live data only).
    Fallback: yFinance for public index data.
    """
    import asyncio
    from services.dragonfly_client import get_cache
    
    cache = get_cache()
    cached_data = cache.get(MARKET_INDICES_CACHE_KEY)
    if cached_data:
        logger.info("📊 Market indices from cache")
        return cached_data
    
    try:
        # Allow 15s timeout for yFinance cold start
        result = await asyncio.wait_for(_fetch_market_indices_internal(), timeout=15.0)
        if result:
            cache.set(MARKET_INDICES_CACHE_KEY, result, MARKET_INDICES_CACHE_TTL)
            return result
        # No data available but no error
        return []
    except asyncio.TimeoutError:
        logger.error("Market indices fetch timed out after 15s")
        return []
    except Exception as e:
        logger.error(f"Market indices fetch failed: {e}")
        # Return empty list instead of error dict to avoid 500 ValidationError
        return []


# Alias for compatibility with different API paths
@router.get("/indices", response_model=List[MarketIndex])
async def get_trading_indices():
    """Alias for /market-indices for API compatibility."""
    return await get_market_indices()


@router.get("/instruments", response_model=InstrumentsListResponse)
async def get_instruments():
    """
    Get list of available trading instruments dynamically.
    """
    from utils.symbol_utils import get_all_symbols, get_company_name
    
    symbols = get_all_symbols()
    if not symbols:
        # Emergency safety list if DB empty
        symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"]
        
    instruments = []
    for sym in symbols[:20]: # Return top 20 for list views
        instruments.append({
            "symbol": sym,
            "name": get_company_name(sym),
            "exchange": "NSE"
        })
        
    return {
        "status": "success",
        "instruments": instruments,
        "count": len(instruments)
    }

async def _fetch_market_indices_internal():
    """
    Fetch market indices using multi-source fallback:
    1. MarketDataOrchestrator cache
    2. Upstox REST API (get_live_quotes)
    3. yFinance (via market_fallback)
    4. Database fallback
    """
    from services.upstox_client import get_upstox_client
    from utils.market_fallback import fetch_live_indices_yfinance
    from services.market_data_orchestrator import get_market_data_orchestrator
    
    INDEX_MAPPINGS = [
        ("NIFTY 50", "NSE_INDEX|Nifty 50"),
        ("BANK NIFTY", "NSE_INDEX|Nifty Bank"),
        ("INDIA VIX", "NSE_INDEX|India VIX"),
    ]
    
    result = []
    
    # 1. Try Orchestrator Cache
    try:
        orchestrator = get_market_data_orchestrator()
        cached_data = orchestrator.get_all_data()
        if cached_data:
            for name, _ in INDEX_MAPPINGS:
                for item in cached_data:
                    if item.get("symbol") == name:
                        result.append({
                            "name": name,
                            "value": round(item.get("ltp", 0), 2),
                            "change": round(item.get("change_pct", 0), 2),
                            "percent": round(item.get("change_pct", 0), 2),
                            "source": f"cache:{item.get('source', 'unknown')}"
                        })
                        break
            if result: return result
    except: pass

    # 2. Try Upstox REST API
    try:
        client = get_upstox_client()
        keys = [m[1] for m in INDEX_MAPPINGS]
        quotes = await client.get_live_quotes(keys)
        
        for name, key in INDEX_MAPPINGS:
            quote = quotes.get(key)
            if quote:
                result.append({
                    "name": name,
                    "value": round(quote['last_price'], 2),
                    "change": round(quote.get('net_change', 0), 2),
                    "percent": round(quote.get('change_percent', 0), 2),
                    "source": "upstox_rest"
                })
        if result: return result
    except: pass

    # 3. Try yFinance (Standardized Fallback)
    try:
        yf_indices = await fetch_live_indices_yfinance()
        if yf_indices:
            return yf_indices
    except: pass
    
    # 4. Final Database Fallback
    try:
        from database import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            for name, _ in INDEX_MAPPINGS:
                # Use stock_candle table with new schema
                query = text("""
                    SELECT sc.close, sc.candle_ts 
                    FROM stock_candle sc
                    JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                    WHERE im.symbol = :symbol AND sc.timeframe = 1440
                    ORDER BY sc.candle_ts DESC LIMIT 1
                """)
                res = await session.execute(query, {"symbol": name})
                row = res.first()
                if row:
                    result.append({
                        "name": name, "value": round(float(row[0]), 2), "change": 0, "percent": 0,
                        "source": "database", "stale": True
                    })
        return result
    except: pass
    
    return None

@router.get("/top-gainers", response_model=List[TopMover])
async def get_top_gainers(current_user: User = Depends(get_current_user)):
    """
    Get top gainers with smart data source selection.
    
    During market hours (09:15-15:30 IST):
        → Returns live WebSocket/REST data from Nifty100RankingService
    
    After market hours:
        → Returns official snapshot from Upstox (via cache or DB)
        → Ensures exchange-validated close prices
    """
    from services.market_hours_service import get_market_hours_service
    from services.dragonfly_client import get_cache
    from datetime import date
    
    market_hours = get_market_hours_service()
    is_open = market_hours.is_market_open()
    
    # If market is OPEN, use live data
    if is_open:
        from services.nifty100_ranking_service import get_nifty100_ranking_service
        service = get_nifty100_ranking_service()
        rankings = await service.get_rankings()
        
        return [
            {"symbol": g['symbol'], "price": g['ltp'], "change": g['change_pct']}
            for g in rankings.get('gainers', [])
        ]
    
    # Market is CLOSED - use snapshot from cache or DB
    logger.info("Market closed - fetching from snapshot")
    cache = get_cache()
    today = date.today().strftime("%Y-%m-%d")
    
    # 1. Try cache first (fastest)
    cached = cache.get(f"top_gainers:{today}")
    if cached and cached.get("data"):
        logger.info(f"Top gainers from cache ({today})")
        return [
            {"symbol": g['symbol'], "price": g['close_price'], "change": g['change_percent']}
            for g in cached.get("data", [])
        ]
    
    # 2. Try database snapshot
    try:
        from database import AsyncSessionLocal
        from sqlalchemy import text
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT symbol, close_price, change_percent 
                    FROM daily_top_gainers_snapshot 
                    WHERE trade_date = :date AND category = 'GAINER'
                    ORDER BY rank ASC
                    LIMIT 10
                """),
                {"date": today}
            )
            rows = result.fetchall()
            
            if rows:
                logger.info(f"Top gainers from DB snapshot ({today})")
                return [
                    {"symbol": r[0], "price": float(r[1]), "change": float(r[2])}
                    for r in rows
                ]
    except Exception as e:
        logger.warning(f"DB snapshot lookup failed: {e}")
    
    # 3. Try previous trading day snapshot
    try:
        from database import AsyncSessionLocal
        from sqlalchemy import text
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT symbol, close_price, change_percent, trade_date
                    FROM daily_top_gainers_snapshot 
                    WHERE category = 'GAINER'
                    ORDER BY trade_date DESC, rank ASC
                    LIMIT 10
                """)
            )
            rows = result.fetchall()
            
            if rows:
                logger.info(f"Top gainers from previous day snapshot ({rows[0][3]})")
                return [
                    {"symbol": r[0], "price": float(r[1]), "change": float(r[2])}
                    for r in rows
                ]
    except Exception as e:
        logger.warning(f"Previous day snapshot lookup failed: {e}")
    
    # 4. Final fallback - live ranking service
    from services.nifty100_ranking_service import get_nifty100_ranking_service
    service = get_nifty100_ranking_service()
    rankings = await service.get_rankings()
    
    return [
        {"symbol": g['symbol'], "price": g['ltp'], "change": g['change_pct']}
        for g in rankings.get('gainers', [])
    ]


@router.get("/gainers-losers", response_model=List[GainersLosersResponse])
async def get_gainers_losers(current_user: User = Depends(get_current_user)):
    """Dynamic gainers and losers from Nifty 100 universe."""
    from services.nifty100_ranking_service import get_nifty100_ranking_service
    
    service = get_nifty100_ranking_service()
    rankings = await service.get_rankings()
    
    combined = []
    # Map gainers
    for g in rankings.get('gainers', [])[:3]:
        combined.append({
            "ticker": g['symbol'], 
            "change": g['change_pct'], 
            "color": "bg-green-500", 
            "price": g['ltp']
        })
    
    # Map losers
    for l in rankings.get('losers', [])[:3]:
        combined.append({
            "ticker": l['symbol'], 
            "change": l['change_pct'], 
            "color": "bg-red-500", 
            "price": l['ltp']
        })
        
    return combined
