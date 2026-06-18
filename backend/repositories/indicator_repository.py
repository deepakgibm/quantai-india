from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
from datetime import datetime
from models_indicators import PrecomputedIndicator, IndicatorComputeJob

class IndicatorRepository:
    @staticmethod
    async def get_latest_indicators(db: AsyncSession, symbol: str, interval: str = "1d") -> Optional[PrecomputedIndicator]:
        """Get the latest precomputed indicator values for a symbol."""
        stmt = select(PrecomputedIndicator).where(
            PrecomputedIndicator.symbol == symbol,
            PrecomputedIndicator.interval == interval
        ).order_by(PrecomputedIndicator.timestamp.desc()).limit(1)
        res = await db.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def get_historical_indicators(
        db: AsyncSession, symbol: str, interval: str = "1d", limit: int = 300
    ) -> List[PrecomputedIndicator]:
        """Fetch historical precomputed indicators for a symbol, ordered by timestamp ascending."""
        stmt = select(PrecomputedIndicator).where(
            PrecomputedIndicator.symbol == symbol,
            PrecomputedIndicator.interval == interval
        ).order_by(PrecomputedIndicator.timestamp.desc()).limit(limit)
        res = await db.execute(stmt)
        # return reversed to have chronological order
        return list(reversed(res.scalars().all()))

    @staticmethod
    async def save_indicator(db: AsyncSession, indicator: PrecomputedIndicator) -> PrecomputedIndicator:
        """Save a precomputed indicator."""
        db.add(indicator)
        await db.flush()
        return indicator

    @staticmethod
    async def get_job_by_id(db: AsyncSession, job_id: str) -> Optional[IndicatorComputeJob]:
        """Get indicator computation job details."""
        stmt = select(IndicatorComputeJob).where(IndicatorComputeJob.job_id == job_id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def create_job(db: AsyncSession, job: IndicatorComputeJob) -> IndicatorComputeJob:
        """Create a new indicator computation tracking job."""
        db.add(job)
        await db.flush()
        return job
