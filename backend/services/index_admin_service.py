import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from models_alpha import IndexMaster, IndexConstituent, InstrumentMaster

logger = logging.getLogger(__name__)

class IndexAdminService:
    async def create_index(self, db: AsyncSession, name: str, description: str = "", base_index_id: Optional[int] = None) -> IndexMaster:
        """Create a new index definition."""
        # Check if exists
        res = await db.execute(select(IndexMaster).where(IndexMaster.index_name == name))
        if res.scalar_one_or_none():
            raise ValueError(f"Index {name} already exists")

        new_index = IndexMaster(
            index_name=name,
            description=description,
            base_index_id=base_index_id
        )
        db.add(new_index)
        await db.commit()
        await db.refresh(new_index)
        return new_index

    async def add_constituent(self, db: AsyncSession, index_id: int, symbol: str) -> bool:
        """Add a stock symbol to an index."""
        # Find instrument
        res = await db.execute(select(InstrumentMaster).where(InstrumentMaster.symbol == symbol))
        instrument = res.scalar_one_or_none()
        if not instrument:
            raise ValueError(f"Symbol {symbol} not found in instrument master")

        # Check if already in index
        res = await db.execute(select(IndexConstituent).where(
            IndexConstituent.index_id == index_id,
            IndexConstituent.instrument_id == instrument.instrument_id
        ))
        if res.scalar_one_or_none():
            return True # Already exists

        new_mapping = IndexConstituent(
            index_id=index_id,
            instrument_id=instrument.instrument_id
        )
        db.add(new_mapping)
        await db.commit()
        return True

    async def remove_constituent(self, db: AsyncSession, index_id: int, symbol: str) -> bool:
        """Remove a stock symbol from an index."""
        res = await db.execute(select(InstrumentMaster).where(InstrumentMaster.symbol == symbol))
        instrument = res.scalar_one_or_none()
        if not instrument:
            raise ValueError(f"Symbol {symbol} not found")

        await db.execute(delete(IndexConstituent).where(
            IndexConstituent.index_id == index_id,
            IndexConstituent.instrument_id == instrument.instrument_id
        ))
        await db.commit()
        return True

    async def delete_index(self, db: AsyncSession, index_id: int) -> bool:
        """Soft or hard delete an index."""
        # First remove constituents
        await db.execute(delete(IndexConstituent).where(IndexConstituent.index_id == index_id))
        # Then the index itself
        await db.execute(delete(IndexMaster).where(IndexMaster.index_id == index_id))
        await db.commit()
        return True

_index_admin_service = None
def get_index_admin_service():
    global _index_admin_service
    if _index_admin_service is None:
        _index_admin_service = IndexAdminService()
    return _index_admin_service
