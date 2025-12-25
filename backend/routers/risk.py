from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import User, UserSettings
from utils.auth import get_current_user

router = APIRouter()

@router.get("/")
async def get_risk_settings(
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
        "current_capital_used": 250000.00,
        "available_capital": settings.max_capital - 250000.00,
        "max_loss_per_trade": settings.max_capital * (settings.max_risk_per_trade / 100)
    }

@router.put("/")
async def update_risk_settings(
    max_capital: float = None,
    max_risk_per_trade: float = None,
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
    
    await db.commit()
    return {"message": "Risk settings updated successfully"}
