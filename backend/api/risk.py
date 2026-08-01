from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import User, RiskConfig
from utils.auth import get_current_user
from sqlalchemy import select

router = APIRouter(tags=["Risk Settings"])

@router.get("/")
async def get_risk_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(RiskConfig).where(RiskConfig.user_id == current_user.id)
        res = await db.execute(stmt)
        config = res.scalar_one_or_none()
        if not config:
            return {
                "max_daily_loss": 5000.0,
                "max_position_size": 50000.0,
                "max_open_positions": 5
            }
        return {
            "max_daily_loss": config.max_daily_loss,
            "max_position_size": config.max_position_size,
            "max_open_positions": config.max_open_positions
        }
    except Exception:
        return {
            "max_daily_loss": 5000.0,
            "max_position_size": 50000.0,
            "max_open_positions": 5
        }
