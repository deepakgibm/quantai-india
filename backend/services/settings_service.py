import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from models import UserSettings
from repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

class SettingsService:
    @staticmethod
    async def get_user_settings(user_id: int, db: AsyncSession) -> UserSettings:
        """Get user settings or create default ones if not present."""
        settings = await UserRepository.get_settings(db, user_id)
        if not settings:
            settings = UserSettings(
                user_id=user_id,
                max_capital=1000000.0,
                max_risk_per_trade=2.0,
                auto_trade=False,
                notifications=True
            )
            await UserRepository.create_settings(db, settings)
            await db.commit()
            await db.refresh(settings)
        return settings

    @staticmethod
    async def update_user_settings(user_id: int, db: AsyncSession, **kwargs) -> UserSettings:
        """Update existing or new settings for a user."""
        # 1. Enforce strict validations
        max_capital = kwargs.get("max_capital")
        if max_capital is not None and max_capital <= 0:
            raise ValueError("Max capital must be strictly positive")

        max_risk_per_trade = kwargs.get("max_risk_per_trade")
        if max_risk_per_trade is not None and (max_risk_per_trade < 0 or max_risk_per_trade > 100):
            raise ValueError("Max risk per trade must be between 0 and 100 percent")

        settings = await UserRepository.get_settings(db, user_id)
        if not settings:
            settings = UserSettings(user_id=user_id)
            await UserRepository.create_settings(db, settings)

        for key, val in kwargs.items():
            if val is not None and hasattr(settings, key):
                setattr(settings, key, val)

        await db.commit()
        await db.refresh(settings)
        return settings

_settings_service = None
def get_settings_service() -> SettingsService:
    global _settings_service
    if _settings_service is None:
        _settings_service = SettingsService()
    return _settings_service
