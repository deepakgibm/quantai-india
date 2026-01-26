import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException

from models import User, UserSettings, Position

logger = logging.getLogger(__name__)

class RiskService:
    async def get_user_risk_stats(self, current_user: User, db: AsyncSession) -> Dict[str, Any]:
        """Fetch user risk settings and current capital usage."""
        settings_result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == current_user.id)
        )
        settings = settings_result.scalar_one_or_none()
        
        if not settings:
            raise HTTPException(status_code=404, detail="Risk settings not found")
            
        pos_result = await db.execute(
            select(func.sum(Position.avg_price * Position.quantity)).where(Position.user_id == current_user.id)
        )
        current_capital_used = pos_result.scalar() or 0.0
        
        return {
            "max_capital": settings.max_capital,
            "max_risk_per_trade": settings.max_risk_per_trade,
            "auto_trade": settings.auto_trade,
            "notifications": settings.notifications,
            "current_capital_used": float(current_capital_used),
            "available_capital": float(settings.max_capital - current_capital_used),
            "max_loss_per_trade": float(settings.max_capital * (settings.max_risk_per_trade / 100))
        }

    async def update_risk_settings(
        self, 
        current_user: User, 
        db: AsyncSession,
        max_capital: Optional[float] = None,
        max_risk_per_trade: Optional[float] = None,
        auto_trade: Optional[bool] = None,
        notifications: Optional[bool] = None
    ) -> Dict[str, str]:
        """Update user risk and general settings."""
        if max_capital is not None and max_capital <= 0:
            raise HTTPException(status_code=400, detail="max_capital must be greater than 0")
        if max_risk_per_trade is not None and (max_risk_per_trade < 0 or max_risk_per_trade > 100):
            raise HTTPException(status_code=400, detail="max_risk_per_trade must be between 0 and 100")

        result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == current_user.id)
        )
        settings = result.scalar_one_or_none()
        if not settings:
            raise HTTPException(status_code=404, detail="Settings not found")
        
        if max_capital is not None:
            settings.max_capital = max_capital
        if max_risk_per_trade is not None:
            settings.max_risk_per_trade = max_risk_per_trade
        if auto_trade is not None:
            settings.auto_trade = auto_trade
        if notifications is not None:
            settings.notifications = notifications
        
        await db.commit()
        return {"message": "Settings updated successfully"}

_risk_service = None
def get_risk_service():
    global _risk_service
    if _risk_service is None:
        _risk_service = RiskService()
    return _risk_service
