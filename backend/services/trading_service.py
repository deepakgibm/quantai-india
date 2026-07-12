import logging
import asyncio
from datetime import datetime, date
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date, text

from models import User, Order, Algorithm, UserSettings, Position, BacktestResult
from database import AsyncSessionLocal
from services.dragonfly_client import get_cache
from services.market_hours_service import get_market_hours_service
from services.upstox_client import get_upstox_client
from utils.market_fallback import fetch_live_indices_yfinance
from services.market_data_orchestrator import get_market_data_orchestrator
from utils.symbol_utils import get_all_symbols, get_company_name

logger = logging.getLogger(__name__)

class TradingService:
    def __init__(self):
        self.MARKET_INDICES_CACHE_KEY = "qai:market:indices"
        self.MARKET_INDICES_CACHE_TTL = 300

    async def get_dashboard_stats(self, current_user: User, db: AsyncSession) -> Dict[str, Any]:
        """Returns dashboard statistics including real-time P&L and capital usage."""
        today = datetime.utcnow().date()
        
        # 1. Get User Trading Config
        settings_result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == current_user.id)
        )
        user_settings = settings_result.scalar_one_or_none()
        total_capital = user_settings.max_capital if user_settings else 1000000.00
        
        # 2. Get Real-time Position Stats
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
        
        today_orders_result = await db.execute(
            select(Order).where(
                Order.user_id == current_user.id,
                cast(Order.timestamp, Date) == today,
                Order.status == 'COMPLETED'
            )
        )
        today_orders = today_orders_result.scalars().all()
        daily_pnl = sum([((o.price or 0) * 0.01) for o in today_orders]) if today_orders else 0.0

        # 4. Get active algorithms
        active_algos_result = await db.execute(
            select(func.count(Algorithm.id)).where(
                Algorithm.user_id == current_user.id,
                Algorithm.is_active == True
            )
        )
        active_algorithms = active_algos_result.scalar() or 0
        
        # 5. Get aggregate win rate
        win_rate_result = await db.execute(
            select(func.avg(BacktestResult.win_rate)).limit(1)
        )
        avg_win_rate = win_rate_result.scalar() or 70.0 
        
        return {
            "total_pnl": round(total_pnl, 2),
            "daily_pnl": round(daily_pnl, 2),
            "capital_used": round(capital_used, 2),
            "total_capital": total_capital,
            "active_algorithms": active_algorithms,
            "win_rate": round(float(avg_win_rate), 1),
            "total_trades": total_trades
        }

    async def get_market_indices(self) -> List[Dict[str, Any]]:
        """Fetch market indices with multi-source fallback and caching."""
        cache = get_cache()
        cached_data = cache.get(self.MARKET_INDICES_CACHE_KEY)
        if cached_data:
            return cached_data
        
        try:
            result = await asyncio.wait_for(self._fetch_market_indices_internal(), timeout=15.0)
            if result:
                cache.set(self.MARKET_INDICES_CACHE_KEY, result, self.MARKET_INDICES_CACHE_TTL)
                return result
            return []
        except Exception as e:
            logger.error(f"Market indices fetch failed: {e}")
            return []

    async def get_instruments(self) -> List[Dict[str, Any]]:
        """Get list of available trading instruments."""
        symbols = get_all_symbols()
        if not symbols:
            symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"]
            
        instruments = []
        for sym in symbols[:20]: 
            instruments.append({
                "symbol": sym,
                "name": get_company_name(sym),
                "exchange": "NSE"
            })
        return instruments

    async def get_top_gainers(self) -> List[Dict[str, Any]]:
        """Get top gainers using live data or snapshots."""
        market_hours = get_market_hours_service()
        if market_hours.is_market_open():
            from services.nifty100_ranking_service import get_nifty100_ranking_service
            service = get_nifty100_ranking_service()
            rankings = await service.get_rankings()
            return [
                {"symbol": g['symbol'], "price": g['ltp'], "change": g['change_pct']}
                for g in rankings.get('gainers', [])
            ]
        
        # Fallback to snapshots
        cache = get_cache()
        today = date.today().strftime("%Y-%m-%d")
        cached = cache.get(f"top_gainers:{today}")
        if cached and cached.get("data"):
            return [{"symbol": g['symbol'], "price": g['close_price'], "change": g['change_percent']} for g in cached.get("data", [])]
        
        try:
            async with AsyncSessionLocal() as session:
                res = await session.execute(text("SELECT symbol, close_price, change_percent FROM daily_top_gainers_snapshot WHERE trade_date = :date AND category = 'GAINER' ORDER BY rank ASC LIMIT 10"), {"date": today})
                rows = res.fetchall()
                if rows: return [{"symbol": r[0], "price": float(r[1]), "change": float(r[2])} for r in rows]
                
                res = await session.execute(text("SELECT symbol, close_price, change_percent FROM daily_top_gainers_snapshot WHERE category = 'GAINER' ORDER BY trade_date DESC, rank ASC LIMIT 10"))
                rows = res.fetchall()
                if rows: return [{"symbol": r[0], "price": float(r[1]), "change": float(r[2])} for r in rows]
        except Exception as e:
            logger.warning(f"Snapshot lookup failed: {e}")
            
        from services.nifty100_ranking_service import get_nifty100_ranking_service
        service = get_nifty100_ranking_service()
        rankings = await service.get_rankings()
        return [{"symbol": g['symbol'], "price": g['ltp'], "change": g['change_pct']} for g in rankings.get('gainers', [])]

    async def _fetch_market_indices_internal(self) -> List[Dict[str, Any]]:
        """Internal unified fetcher for indices using PriceService."""
        INDEX_MAPPINGS = {
            "NIFTY 50": "NIFTY 50",
            "BANK NIFTY": "NIFTY BANK",
            "INDIA VIX": "INDIA VIX",
        }
        
        from services.price_manager import get_price_service
        price_svc = get_price_service()
        
        symbols_to_fetch = list(INDEX_MAPPINGS.values())
        prices = await price_svc.get_prices_bulk(symbols_to_fetch)
        
        results = []
        for name, sym in INDEX_MAPPINGS.items():
            p_data = prices.get(sym)
            if p_data:
                results.append({
                    "name": name,
                    "value": round(p_data.get("ltp", 0.0), 2),
                    "change": round(p_data.get("change", 0.0), 2),
                    "percent": round(p_data.get("change_percent", 0.0), 2),
                    "source": p_data.get("source", "UNKNOWN"),
                    "stale": p_data.get("market_status") != "OPEN"
                })
        return results

_trading_service = None
def get_trading_service():
    global _trading_service
    if _trading_service is None:
        _trading_service = TradingService()
    return _trading_service
