from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from database import get_db
from models import User
from utils.auth import get_current_user
from services.settings_service import get_settings_service

router = APIRouter()

@router.get("/")
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        service = get_settings_service()
        settings = await service.get_user_settings(current_user.id, db)
        return {
            "max_capital": settings.max_capital,
            "max_risk_per_trade": settings.max_risk_per_trade,
            "auto_trade": settings.auto_trade,
            "notifications": settings.notifications
        }
    except Exception:
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
        service = get_settings_service()
        settings = await service.update_user_settings(
            current_user.id,
            db,
            max_capital=max_capital,
            max_risk_per_trade=max_risk_per_trade,
            auto_trade=auto_trade,
            notifications=notifications
        )
        return {
            "max_capital": settings.max_capital,
            "max_risk_per_trade": settings.max_risk_per_trade,
            "auto_trade": settings.auto_trade,
            "notifications": settings.notifications
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
