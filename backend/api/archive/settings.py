from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database import get_db
from models import User
from utils.auth import get_current_user
from services.risk_service import get_risk_service

router = APIRouter()
risk_service = get_risk_service()

@router.get("/")
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stats = await risk_service.get_user_risk_stats(current_user, db)
    return {
        "max_capital": stats["max_capital"],
        "max_risk_per_trade": stats["max_risk_per_trade"],
        "auto_trade": stats["auto_trade"],
        "notifications": stats["notifications"]
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
    return await risk_service.update_risk_settings(current_user, db, max_capital=max_capital, max_risk_per_trade=max_risk_per_trade, auto_trade=auto_trade, notifications=notifications)
