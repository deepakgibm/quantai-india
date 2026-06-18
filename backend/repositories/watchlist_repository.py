from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text
from typing import List, Optional
from datetime import datetime
from models import WatchlistItem

class WatchlistRepository:
    @staticmethod
    async def get_by_user_and_symbol(db: AsyncSession, user_id: int, symbol: str) -> Optional[WatchlistItem]:
        """Check if user has symbol in watchlist."""
        stmt = select(WatchlistItem).where(
            WatchlistItem.user_id == user_id,
            WatchlistItem.symbol == symbol
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def get_all_by_user(db: AsyncSession, user_id: int) -> List[WatchlistItem]:
        """Fetch all watchlist items for a user ordered by added_at desc."""
        stmt = select(WatchlistItem).where(
            WatchlistItem.user_id == user_id
        ).order_by(WatchlistItem.added_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def add(db: AsyncSession, item: WatchlistItem) -> WatchlistItem:
        """Add new watchlist item."""
        db.add(item)
        await db.flush()
        return item

    @staticmethod
    async def delete_by_user_and_symbol(db: AsyncSession, user_id: int, symbol: str) -> bool:
        """Delete watchlist item by user and symbol."""
        stmt = delete(WatchlistItem).where(
            WatchlistItem.user_id == user_id,
            WatchlistItem.symbol == symbol
        )
        res = await db.execute(stmt)
        return res.rowcount > 0

    @staticmethod
    async def get_instrument_details(db: AsyncSession, symbol: str, exchange: str = "NSE") -> Optional[tuple]:
        """Resolve instrument details from instrument_master."""
        sql = text("""
            SELECT instrument_id, company_name, instrument_key
            FROM instrument_master
            WHERE symbol = :symbol AND exchange = :exchange AND is_active = TRUE
            LIMIT 1
        """)
        result = await db.execute(sql, {"symbol": symbol, "exchange": exchange})
        row = result.fetchone()
        if not row:
            # Fallback
            sql_fallback = text("""
                SELECT instrument_id, company_name, instrument_key, exchange
                FROM instrument_master
                WHERE symbol = :symbol AND is_active = TRUE
                LIMIT 1
            """)
            result = await db.execute(sql_fallback, {"symbol": symbol})
            row = result.fetchone()
            if row:
                return row.instrument_id, row.company_name, row.instrument_key, row.exchange
            return None
        return row.instrument_id, row.company_name, row.instrument_key, exchange

    @staticmethod
    async def get_instrument_keys_map(db: AsyncSession, symbols: List[str]) -> dict:
        """Fetch instrument keys for a list of symbols."""
        sql = text("""
            SELECT symbol, instrument_key
            FROM instrument_master
            WHERE symbol = ANY(:symbols) AND is_active = TRUE
        """)
        result = await db.execute(sql, {"symbols": symbols})
        return {row.symbol: row.instrument_key for row in result.fetchall() if row.instrument_key}
