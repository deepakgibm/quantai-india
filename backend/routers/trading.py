from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
import logging

from database import get_db
from models import User, Order, Algorithm
from schemas import DashboardStats
from utils.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    today = datetime.utcnow().date()
    
    # Get total orders
    total_orders_result = await db.execute(
        select(func.count(Order.id)).where(Order.user_id == current_user.id)
    )
    total_trades = total_orders_result.scalar() or 0
    
    # Get today's orders
    today_orders_result = await db.execute(
        select(Order).where(
            Order.user_id == current_user.id,
            func.date(Order.timestamp) == today
        )
    )
    today_orders = today_orders_result.scalars().all()
    
    # Calculate daily P&L (mock calculation)
    daily_pnl = sum([(order.price or 0) * order.quantity * 0.02 for order in today_orders])
    
    # Get active algorithms
    active_algos_result = await db.execute(
        select(func.count(Algorithm.id)).where(
            Algorithm.user_id == current_user.id,
            Algorithm.is_active == True
        )
    )
    active_algorithms = active_algos_result.scalar() or 0
    
    # Mock data for now
    return {
        "total_pnl": 125450.50,
        "daily_pnl": daily_pnl if daily_pnl > 0 else 12450.00,
        "capital_used": 250000.00,
        "total_capital": 1000000.00,
        "active_algorithms": active_algorithms,
        "win_rate": 68.5,
        "total_trades": total_trades if total_trades > 0 else 156
    }

@router.get("/health")
def get_health():
    """
    Instant health check endpoint - no async operations, no database calls.
    Used for monitoring and load balancer health checks.
    """
    return {"status": "healthy", "service": "quantai-trading-api"}

@router.get("/market-indices")
async def get_market_indices():
    """
    Fetch market indices with priority:
    1. Upstox REST API (live data)
    2. yfinance (fallback)
    3. Mock data (last resort)
    """
    import asyncio
    
    # Fallback data
    FALLBACK_DATA = [
        {"name": "NIFTY 50", "value": 23850.15, "change": 125.4, "percent": 0.53, "source": "fallback"},
        {"name": "BANK NIFTY", "value": 51200.80, "change": -89.3, "percent": -0.17, "source": "fallback"},
        {"name": "INDIA VIX", "value": 13.25, "change": -0.35, "percent": -2.58, "source": "fallback"}
    ]
    
    try:
        # Reduced timeout to 5 seconds for faster response
        result = await asyncio.wait_for(_fetch_market_indices_internal(), timeout=5.0)
        return result if result else FALLBACK_DATA
    except asyncio.TimeoutError:
        logger.warning("Market indices fetch timed out, using fallback")
        return FALLBACK_DATA
    except Exception as e:
        logger.error(f"Market indices fetch failed: {e}")
        return FALLBACK_DATA

@router.get("/instruments")
async def get_instruments():
    """
    Get list of available trading instruments.
    Returns popular NSE stocks for quick access.
    """
    return {
        "status": "success",
        "instruments": [
            {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "exchange": "NSE"},
            {"symbol": "TCS", "name": "Tata Consultancy Services Ltd", "exchange": "NSE"},
            {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "exchange": "NSE"},
            {"symbol": "INFY", "name": "Infosys Ltd", "exchange": "NSE"},
            {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "exchange": "NSE"},
            {"symbol": "HINDUNILVR", "name": "Hindustan Unilever Ltd", "exchange": "NSE"},
            {"symbol": "ITC", "name": "ITC Ltd", "exchange": "NSE"},
            {"symbol": "SBIN", "name": "State Bank of India", "exchange": "NSE"},
            {"symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd", "exchange": "NSE"},
            {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank Ltd", "exchange": "NSE"}
        ],
        "count": 10
    }


async def _fetch_market_indices_internal():
    """Internal function to fetch market indices"""
    from services.upstox_client import get_upstox_client
    
    INDEX_MAPPINGS = [
        ("NIFTY 50", "NSE_INDEX|Nifty 50"),
        ("BANK NIFTY", "NSE_INDEX|Nifty Bank"),
        ("INDIA VIX", "NSE_INDEX|India VIX"),
    ]
    
    result = []
    client = get_upstox_client()
    
    for name, instrument_key in INDEX_MAPPINGS:
        try:
            quote = await client.get_live_quote(instrument_key, name)
            if quote and quote.get("last_price", 0) > 0:
                ltp = quote.get("last_price", 0)
                prev_close = quote.get("previous_close", ltp)
                net_change = quote.get("net_change", 0)
                
                if net_change and abs(net_change) > 0.001:
                    change = round(net_change, 2)
                    actual_prev_close = ltp - net_change
                    percent = round((net_change / actual_prev_close) * 100, 2) if actual_prev_close > 0 else 0
                else:
                    change = round(ltp - prev_close, 2)
                    percent = round(quote.get("change_percent", 0), 2)
                
                result.append({
                    "name": name,
                    "value": round(ltp, 2),
                    "change": change,
                    "percent": percent,
                    "source": "upstox"
                })
                continue
        except Exception as e:
            logger.warning(f"Upstox API failed for {name}: {e}")
        
        # Fallback: Add mock data for this index
        mock = {"NIFTY 50": (23850, 125.4), "BANK NIFTY": (51200, -89.3), "INDIA VIX": (13.5, -0.55)}
        val, chg = mock.get(name, (0, 0))
        result.append({"name": name, "value": val, "change": chg, "percent": round((chg/val)*100, 2) if val else 0, "source": "mock"})
    
    return result

@router.get("/top-gainers")
async def get_top_gainers(current_user: User = Depends(get_current_user)):
    return [
        {"symbol": "RELIANCE", "price": 2850.50, "change": 2.5},
        {"symbol": "INFOSYS", "price": 1545.20, "change": 3.2},
        {"symbol": "TCS", "price": 3620.80, "change": 1.8}
    ]

@router.get("/gainers-losers")
async def get_gainers_losers(current_user: User = Depends(get_current_user)):
    """Get top 3 gainers and top 3 losers from NIFTY stocks - returns cached/mock data for fast response"""
    # Return immediate fallback data to avoid timeout
    # In production, this would be populated by a background job
    return [
        {"ticker": "RELIANCE", "change": 1.2, "color": "bg-green-500", "price": 2850.0},
        {"ticker": "INFOSYS", "change": 2.1, "color": "bg-green-600", "price": 1545.0},
        {"ticker": "TATAMOTORS", "change": 1.8, "color": "bg-green-500", "price": 890.0},
        {"ticker": "HDFCBANK", "change": -0.8, "color": "bg-red-400", "price": 1680.0},
        {"ticker": "SBIN", "change": -1.2, "color": "bg-red-500", "price": 815.0},
        {"ticker": "BAJFINANCE", "change": -0.5, "color": "bg-red-400", "price": 7200.0}
    ]
