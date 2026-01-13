from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import User, UserSettings
from utils.auth import get_current_user, get_optional_user

router = APIRouter()

@router.get("/")
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    
    return {
        "max_capital": settings.max_capital,
        "max_risk_per_trade": settings.max_risk_per_trade,
        "auto_trade": settings.auto_trade,
        "notifications": settings.notifications
    }

@router.put("/")
async def update_settings(
    max_capital: float = None,
    max_risk_per_trade: float = None,
    auto_trade: bool = None,
    notifications: bool = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
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
