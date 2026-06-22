from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from models import BrokerCredentials

class BrokerRepository:
    @staticmethod
    async def get_credentials(db: AsyncSession, user_id: int, broker: str = "upstox") -> Optional[BrokerCredentials]:
        """Fetch active credentials for a specific broker of a user."""
        stmt = select(BrokerCredentials).where(
            BrokerCredentials.user_id == user_id,
            BrokerCredentials.broker == broker,
            BrokerCredentials.is_active == True
        ).limit(1)
        res = await db.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def get_all_by_user(db: AsyncSession, user_id: int) -> List[BrokerCredentials]:
        """Fetch all broker credentials for a user."""
        stmt = select(BrokerCredentials).where(BrokerCredentials.user_id == user_id)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def save_credentials(db: AsyncSession, creds: BrokerCredentials) -> BrokerCredentials:
        """Save new or update existing broker credentials."""
        db.add(creds)
        await db.flush()
        return creds

    @staticmethod
    async def deactivate_all_for_user(db: AsyncSession, user_id: int, broker: str) -> None:
        """Deactivate all active credentials for a broker type of a user."""
        stmt = select(BrokerCredentials).where(
            BrokerCredentials.user_id == user_id,
            BrokerCredentials.broker == broker,
            BrokerCredentials.is_active == True
        )
        res = await db.execute(stmt)
        for creds in res.scalars().all():
            creds.is_active = False
        await db.flush()
