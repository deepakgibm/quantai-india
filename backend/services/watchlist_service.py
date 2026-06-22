import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from models import WatchlistItem
from schemas import WatchlistItemCreate
from repositories.watchlist_repository import WatchlistRepository
from services.upstox_price_resolver import get_upstox_price_resolver

logger = logging.getLogger(__name__)

class WatchlistService:
    @staticmethod
    async def add_to_watchlist(db: AsyncSession, user_id: int, item_in: WatchlistItemCreate) -> Optional[WatchlistItem]:
        """
        Add a stock symbol to the user's watchlist.
        Resolves instrument metadata from instrument_master.
        If baseline price is omitted, retrieves it from live quote or fallback EOD close.
        """
        symbol = item_in.symbol.upper().strip()
        exchange = item_in.exchange.upper().strip() if item_in.exchange else "NSE"

        # Check if already in watchlist for this user
        existing_item = await WatchlistRepository.get_by_user_and_symbol(db, user_id, symbol)
        if existing_item:
            logger.info(f"Symbol {symbol} is already in user {user_id}'s watchlist")
            return None

        # Resolve instrument details
        inst = await WatchlistRepository.get_instrument_details(db, symbol, exchange)
        if not inst:
            logger.error(f"Symbol {symbol} not found in instrument_master")
            return None
        _, company_name, instrument_key, exchange = inst

        added_at = datetime.utcnow()
        watchlist_price = item_in.watchlist_price

        # Fallback price recovery
        if not watchlist_price or watchlist_price <= 0:
            # Attempt 1: Fetch live quote LTP using UpstoxPriceResolver
            try:
                resolver = get_upstox_price_resolver()
                price_res = await resolver.get_price(symbol)
                if price_res and price_res.get("price", 0) > 0:
                    watchlist_price = float(price_res["price"])
                    logger.info(f"Resolved live price for {symbol} via Resolver: {watchlist_price}")
            except Exception as e:
                logger.warning(f"Failed to fetch live quote for {symbol} on watchlist addition: {e}")

            # Attempt 2: Fetch closest historical EOD close
            if not watchlist_price or watchlist_price <= 0:
                try:
                    price_hist = await WatchlistService.get_historical_price_closest_to(
                        instrument_key, symbol, added_at, db
                    )
                    if price_hist and price_hist > 0:
                        watchlist_price = price_hist
                        logger.info(f"Resolved historical fallback price for {symbol}: {watchlist_price}")
                except Exception as e:
                    logger.error(f"Failed to fetch historical price for {symbol}: {e}")

            # Last resort
            if not watchlist_price or watchlist_price <= 0:
                watchlist_price = 0.0
                logger.warning(f"Could not resolve price for {symbol}. Set baseline to 0.0.")

        db_item = WatchlistItem(
            user_id=user_id,
            symbol=symbol,
            company_name=company_name,
            exchange=exchange,
            added_at=added_at,
            watchlist_price=watchlist_price,
            current_price=watchlist_price,
            change_percent=0.0,
            change_amount=0.0,
            last_updated=added_at
        )

        db_item = await WatchlistRepository.add(db, db_item)
        await db.commit()
        await db.refresh(db_item)
        return db_item

    @staticmethod
    async def get_historical_price_closest_to(instrument_key: str, symbol: str, target_date: datetime, db: Optional[AsyncSession] = None) -> Optional[float]:
        """
        Queries local database daily EOD candles for a 7-day window ending at target_date
        to find the EOD closing price closest to the target_date.
        """
        if db is None:
            from database import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                return await WatchlistService.get_historical_price_closest_to(instrument_key, symbol, target_date, session)

        from models_alpha import InstrumentMaster, StockCandle
        from sqlalchemy import select

        # 1. Resolve instrument_id
        stmt = select(InstrumentMaster.instrument_id).where(InstrumentMaster.symbol == symbol.upper())
        res = await db.execute(stmt)
        instrument_id = res.scalar_one_or_none()

        if not instrument_id:
            logger.warning(f"WatchlistService: instrument {symbol} not found in DB")
            return None

        # 2. Query stock_candle daily candles (timeframe=1440) in a 7-day window
        from_date = target_date - timedelta(days=7)
        stmt_candle = (
            select(StockCandle.close, StockCandle.candle_ts)
            .where(
                StockCandle.instrument_id == instrument_id,
                StockCandle.timeframe == 1440,
                StockCandle.candle_ts >= from_date,
                StockCandle.candle_ts <= target_date
            )
            .order_by(StockCandle.candle_ts.desc())
        )
        res_candle = await db.execute(stmt_candle)
        rows = res_candle.all()

        if not rows:
            logger.warning(f"WatchlistService: No daily candles in DB for {symbol} between {from_date} and {target_date}")
            return None

        # The first row is the closest (latest daily candle in the window)
        return float(rows[0][0])

    @staticmethod
    async def get_watchlist(db: AsyncSession, user_id: int) -> List[WatchlistItem]:
        """
        Fetch all watchlist items for the user, update their current prices
        via a single batch live quote fetch, and calculate returns.
        """
        items = await WatchlistRepository.get_all_by_user(db, user_id)

        if not items:
            return []

        # Batch resolve prices via UpstoxPriceResolver
        symbols = [item.symbol for item in items]
        
        if symbols:
            resolver = get_upstox_price_resolver()
            try:
                prices_map = await resolver.get_prices_bulk(symbols)
                
                # Update items with live quote data from resolver
                for item in items:
                    p_data = prices_map.get(item.symbol.upper())
                    if p_data and p_data.get("price", 0) > 0:
                        ltp = float(p_data["price"])
                        item.current_price = ltp
                        wp = item.watchlist_price or 0.0
                        item.change_amount = ltp - wp
                        if wp > 0:
                            item.change_percent = (item.change_amount / wp) * 100
                        else:
                            item.change_percent = 0.0
                        item.last_updated = datetime.utcnow()
                
                await db.commit()
            except Exception as e:
                logger.error(f"Failed to update watchlist live prices in batch via resolver: {e}")

        return items

    @staticmethod
    async def remove_from_watchlist(db: AsyncSession, user_id: int, symbol: str) -> bool:
        """
        Delete a stock symbol from the user's watchlist.
        """
        symbol_upper = symbol.upper().strip()
        success = await WatchlistRepository.delete_by_user_and_symbol(db, user_id, symbol_upper)
        await db.commit()
        return success


    @staticmethod
    def get_days_tracked(added_at: datetime) -> int:
        return max(1, (datetime.utcnow() - added_at).days)

    @staticmethod
    def get_status_label(change_pct: float) -> str:
        if change_pct >= 10.0:
            return "Strong Winner"
        elif change_pct >= 2.0:
            return "Winner"
        elif change_pct <= -10.0:
            return "Strong Loser"
        elif change_pct <= -2.0:
            return "Loser"
        else:
            return "Neutral"

    @staticmethod
    async def get_watchlist_performance(db: AsyncSession, user_id: int, virtual_investment: float = 10000.0) -> Dict[str, Any]:
        """
        Computes virtual performance KPI metrics for the watchlist portfolio.
        """
        # Fetch updated watchlist
        items = await WatchlistService.get_watchlist(db, user_id)
        if not items:
            return {
                "total_value": 0.0,
                "total_pnl": 0.0,
                "pnl_percent": 0.0,
                "total_invested": 0.0,
                "accuracy_percent": 0.0
            }

        total_invested = 0.0
        total_value = 0.0
        winners = 0

        for item in items:
            p_entry = item.watchlist_price or 0.0
            p_curr = item.current_price or p_entry
            
            if p_entry <= 0:
                continue
                
            total_invested += virtual_investment
            shares = virtual_investment / p_entry
            curr_val = shares * p_curr
            total_value += curr_val

            change_pct = ((p_curr - p_entry) / p_entry) * 100
            if change_pct > 0:
                winners += 1

        total_pnl = total_value - total_invested
        pnl_percent = (total_pnl / total_invested) * 100 if total_invested > 0 else 0.0
        accuracy = (winners / len(items)) * 100 if items else 0.0

        return {
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "pnl_percent": round(pnl_percent, 2),
            "total_invested": round(total_invested, 2),
            "accuracy_percent": round(accuracy, 2)
        }

    @staticmethod
    async def get_watchlist_analytics(db: AsyncSession, user_id: int, virtual_investment: float = 10000.0) -> Dict[str, Any]:
        """
        Generates premium dashboard analytics including best/worst picks,
        accuracy, winners/losers pie chart data, top 10 performers bar chart data,
        and daily ROI equity curve.
        """
        items = await WatchlistService.get_watchlist(db, user_id)
        if not items:
            return {
                "best_pick": None,
                "worst_pick": None,
                "fastest_gainer": None,
                "accuracy_percent": 0.0,
                "winners_losers_chart": [],
                "top_performers_chart": [],
                "roi_over_time_chart": []
            }

        # Basic Stats & Best/Worst Picks
        best_item = None
        worst_item = None
        fastest_item = None
        
        best_pct = -999999.0
        worst_pct = 999999.0
        fastest_avg_gain = -999999.0
        winners_count = 0
        losers_count = 0
        neutral_count = 0

        for item in items:
            days = WatchlistService.get_days_tracked(item.added_at)
            p_entry = item.watchlist_price or 0.0
            p_curr = item.current_price or p_entry
            
            if p_entry <= 0:
                continue

            pct = ((p_curr - p_entry) / p_entry) * 100
            
            # Count distribution
            status = WatchlistService.get_status_label(pct)
            if "Winner" in status:
                winners_count += 1
            elif "Loser" in status:
                losers_count += 1
            else:
                neutral_count += 1

            if pct > 0:
                winners_count += 1 # Compatibility count helper

            if pct > best_pct:
                best_pct = pct
                best_item = item
            if pct < worst_pct:
                worst_pct = pct
                worst_item = item

            avg_gain = pct / days
            if avg_gain > fastest_avg_gain:
                fastest_avg_gain = avg_gain
                fastest_item = item

        # Accurate counts for winners/neutral/losers
        total_items = len(items)
        valid_items = [i for i in items if i.watchlist_price and i.watchlist_price > 0]
        accuracy = (sum(1 for item in valid_items if (item.current_price or 0.0) > item.watchlist_price) / len(valid_items)) * 100 if valid_items else 0.0

        best_pick_payload = {
            "symbol": best_item.symbol,
            "company_name": best_item.company_name,
            "change_percent": round(best_pct, 2)
        } if best_item else None

        worst_pick_payload = {
            "symbol": worst_item.symbol,
            "company_name": worst_item.company_name,
            "change_percent": round(worst_pct, 2)
        } if worst_item else None

        fastest_gainer_payload = {
            "symbol": fastest_item.symbol,
            "company_name": fastest_item.company_name,
            "change_percent": round(fastest_item.change_percent or 0.0, 2),
            "days_tracked": WatchlistService.get_days_tracked(fastest_item.added_at)
        } if fastest_item else None

        winners_losers_chart = [
            {"name": "Winners", "value": winners_count, "color": "#10B981"},
            {"name": "Neutral", "value": neutral_count, "color": "#FBBF24"},
            {"name": "Losers", "value": losers_count, "color": "#EF4444"}
        ]

        # Top 10 Performers Chart
        sorted_performers = sorted(items, key=lambda x: x.change_percent or 0.0, reverse=True)[:10]
        top_performers_chart = [
            {"symbol": x.symbol, "change_percent": round(x.change_percent or 0.0, 2)}
            for x in sorted_performers
        ]

        # daily ROI Equity Curve
        roi_over_time_chart = await WatchlistService._calculate_roi_curve(db, items, virtual_investment)

        return {
            "best_pick": best_pick_payload,
            "worst_pick": worst_pick_payload,
            "fastest_gainer": fastest_gainer_payload,
            "accuracy_percent": round(accuracy, 2),
            "winners_losers_chart": winners_losers_chart,
            "top_performers_chart": top_performers_chart,
            "roi_over_time_chart": roi_over_time_chart
        }

    @staticmethod
    async def _calculate_roi_curve(db: AsyncSession, items: List[WatchlistItem], virtual_investment: float) -> List[Dict[str, Any]]:
        """
        Generates daily portfolio ROI points starting from the oldest watchlist entry to today.
        """
        oldest_date = min(item.added_at for item in items)
        today = datetime.utcnow()
        
        # Query instrument_ids for these symbols to fetch their historical database candles
        symbols = [item.symbol for item in items]
        sql = text("""
            SELECT symbol, instrument_id
            FROM instrument_master
            WHERE symbol = ANY(:symbols) AND is_active = TRUE
        """)
        result = await db.execute(sql, {"symbols": symbols})
        symbol_to_id = {row.symbol: row.instrument_id for row in result.fetchall()}
        
        instrument_ids = list(symbol_to_id.values())
        
        symbol_prices = {}
        if instrument_ids:
            # Fetch daily candles (timeframe = 1440)
            candles_sql = text("""
                SELECT im.symbol, sc.candle_ts::date as date, sc.close
                FROM stock_candle sc
                JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                WHERE sc.instrument_id = ANY(:ids)
                  AND sc.timeframe = 1440
                  AND sc.candle_ts >= :start_date
                ORDER BY sc.candle_ts ASC
            """)
            candles_res = await db.execute(candles_sql, {"ids": instrument_ids, "start_date": oldest_date.date()})
            
            for row in candles_res.fetchall():
                d_str = row.date.strftime("%Y-%m-%d")
                if d_str not in symbol_prices:
                    symbol_prices[d_str] = {}
                symbol_prices[d_str][row.symbol] = float(row.close)

        # Generate a timeline from oldest_date to today
        timeline = []
        curr = oldest_date.date()
        end = today.date()
        while curr <= end:
            timeline.append(curr)
            curr += timedelta(days=1)

        # Build equity curve points
        roi_points = []
        last_known_prices = {} # For forward-filling missing daily candles

        for day in timeline:
            day_str = day.strftime("%Y-%m-%d")
            
            daily_total_value = 0.0
            daily_total_invested = 0.0
            
            # Find active items on or before this day
            active_items = [item for item in items if item.added_at.date() <= day]
            
            if not active_items:
                continue

            for item in active_items:
                p_entry = item.watchlist_price or 0.0
                if p_entry <= 0:
                    continue

                # Resolve price for this day
                day_price = symbol_prices.get(day_str, {}).get(item.symbol)
                
                # If it's today, we can fall back to the live current_price
                if day == end and (not day_price or day_price == 0.0):
                    day_price = item.current_price

                # Forward fill helper
                if day_price and day_price > 0.0:
                    last_known_prices[item.symbol] = day_price
                else:
                    day_price = last_known_prices.get(item.symbol, p_entry)
                
                shares = virtual_investment / p_entry
                val = shares * day_price
                
                daily_total_invested += virtual_investment
                daily_total_value += val
            
            roi = ((daily_total_value - daily_total_invested) / daily_total_invested) * 100 if daily_total_invested > 0 else 0.0
            
            # Format and record point
            roi_points.append({
                "date": day_str,
                "roi_percent": round(roi, 2),
                "portfolio_value": round(daily_total_value, 2)
            })

        # Cap the number of return points if timeline is very long to prevent UI lag (e.g. max 90 points, sampling)
        if len(roi_points) > 100:
            step = len(roi_points) // 80
            sampled = roi_points[::step]
            # Ensure today is included
            if roi_points[-1] not in sampled:
                sampled.append(roi_points[-1])
            return sampled
            
        return roi_points
