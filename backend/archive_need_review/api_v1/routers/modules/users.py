from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database import get_db
from models import User
from utils.auth import get_current_user
from services.risk_service import get_risk_service

router = APIRouter(prefix="/users", tags=["Users & Settings (v1)"])
risk_service = get_risk_service()

@router.get("/me", tags=["Profile"])
async def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "is_upstox_connected": current_user.is_upstox_connected
    }

@router.get("/risk", tags=["Risk"])
async def get_risk_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await risk_service.get_user_risk_stats(current_user, db)

@router.put("/risk", tags=["Risk"])
async def update_risk_settings(
    max_capital: Optional[float] = None,
    max_risk_per_trade: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await risk_service.update_risk_settings(
        current_user, db, max_capital=max_capital, max_risk_per_trade=max_risk_per_trade
    )

@router.get("/settings", tags=["Settings"])
async def get_general_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Reuse risk service for settings as they are in the same model
    stats = await risk_service.get_user_risk_stats(current_user, db)
    return {
        "auto_trade": stats["auto_trade"],
        "notifications": stats["notifications"]
    }

@router.put("/settings", tags=["Settings"])
async def update_general_settings(
    auto_trade: Optional[bool] = None,
    notifications: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await risk_service.update_risk_settings(
        current_user, db, auto_trade=auto_trade, notifications=notifications
    )
