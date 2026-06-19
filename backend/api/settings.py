from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from database import get_db
from models import User, UserSettings
from utils.auth import get_current_user
from sqlalchemy import select

router = APIRouter()

@router.get("/")
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(UserSettings).where(UserSettings.user_id == current_user.id)
        res = await db.execute(stmt)
        settings = res.scalar_one_or_none()
        if not settings:
            # Create default settings
            settings = UserSettings(
                user_id=current_user.id,
                max_capital=1000000.0,
                max_risk_per_trade=2.0,
                auto_trade=False,
                notifications=True
            )
            db.add(settings)
            await db.commit()
            await db.refresh(settings)
            
        return {
            "max_capital": settings.max_capital,
            "max_risk_per_trade": settings.max_risk_per_trade,
            "auto_trade": settings.auto_trade,
            "notifications": settings.notifications
        }
    except Exception as e:
        return {
            "max_capital": 1000000.0,
            "max_risk_per_trade": 2.0,
            "auto_trade": False,
            "notifications": True
        }

@router.put("/")
async def update_settings(
    max_capital: Optional[float] = None,
    max_risk_per_trade: Optional[float] = None,
    auto_trade: Optional[bool] = None,
    notifications: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(UserSettings).where(UserSettings.user_id == current_user.id)
        res = await db.execute(stmt)
        settings = res.scalar_one_or_none()
        if not settings:
            settings = UserSettings(user_id=current_user.id)
            db.add(settings)
            
        if max_capital is not None:
            settings.max_capital = max_capital
        if max_risk_per_trade is not None:
            settings.max_risk_per_trade = max_risk_per_trade
        if auto_trade is not None:
            settings.auto_trade = auto_trade
        if notifications is not None:
            settings.notifications = notifications
            
        await db.commit()
        await db.refresh(settings)
        return {
            "max_capital": settings.max_capital,
            "max_risk_per_trade": settings.max_risk_per_trade,
            "auto_trade": settings.auto_trade,
            "notifications": settings.notifications
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
