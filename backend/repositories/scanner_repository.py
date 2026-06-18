from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
from models import ScannerPreset

class ScannerRepository:
    @staticmethod
    async def get_presets_by_user(db: AsyncSession, user_id: int) -> List[ScannerPreset]:
        """Retrieve all scanner presets created by a user."""
        stmt = select(ScannerPreset).where(ScannerPreset.user_id == user_id).order_by(ScannerPreset.created_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_preset_by_id(db: AsyncSession, preset_id: int) -> Optional[ScannerPreset]:
        """Fetch a specific scanner preset by ID."""
        stmt = select(ScannerPreset).where(ScannerPreset.id == preset_id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def save_preset(db: AsyncSession, preset: ScannerPreset) -> ScannerPreset:
        """Create or update a scanner preset."""
        db.add(preset)
        await db.flush()
        return preset

    @staticmethod
    async def delete_preset(db: AsyncSession, preset_id: int, user_id: int) -> bool:
        """Delete a scanner preset belonging to a user."""
        stmt = delete(ScannerPreset).where(
            ScannerPreset.id == preset_id,
            ScannerPreset.user_id == user_id
        )
        res = await db.execute(stmt)
        return res.rowcount > 0
