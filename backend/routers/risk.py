from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database import get_db
from models import User
from utils.auth import get_current_user
from services.risk_service import get_risk_service

router = APIRouter()
risk_service = get_risk_service()

@router.get("/")
async def get_risk_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await risk_service.get_user_risk_stats(current_user, db)

@router.put("/")
async def update_risk_settings(
    max_capital: Optional[float] = None,
    max_risk_per_trade: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await risk_service.update_risk_settings(current_user, db, max_capital=max_capital, max_risk_per_trade=max_risk_per_trade)
