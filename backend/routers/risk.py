from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from database import get_db
from models import User, UserSettings, Position
from utils.auth import get_current_user

router = APIRouter()

@router.get("/")
async def get_risk_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Query for user settings
    settings_result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings = settings_result.scalar_one_or_none()
    
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
        
    # Calculate real-time capital used (sum of avg_price * quantity across all open positions)
    pos_result = await db.execute(
        select(func.sum(Position.avg_price * Position.quantity)).where(Position.user_id == current_user.id)
    )
    current_capital_used = pos_result.scalar() or 0.0
    
    return {
        "max_capital": settings.max_capital,
        "max_risk_per_trade": settings.max_risk_per_trade,
        "current_capital_used": float(current_capital_used),
        "available_capital": float(settings.max_capital - current_capital_used),
        "max_loss_per_trade": float(settings.max_capital * (settings.max_risk_per_trade / 100))
    }

@router.put("/")
async def update_risk_settings(
    max_capital: float = None,
    max_risk_per_trade: float = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
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
    
    await db.commit()
    return {"message": "Risk settings updated successfully"}
