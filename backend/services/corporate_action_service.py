import pandas as pd
from datetime import datetime
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from models_alpha import CorporateAction
from database import AsyncSessionLocal

logger = logging.getLogger(__name__)

async def seed_corporate_actions():
    """Seed the database with known historical corporate actions."""
    actions_to_seed = [
        {
            "symbol": "VEDL",
            "action_type": "Demerger",
            "effective_date": datetime(2026, 4, 30),
            "adjustment_factor": 0.35,
            "ratio": "1:1 demerger",
            "source": "NSE Circular",
            "verified": True
        },
        {
            "symbol": "TATASTEEL",
            "action_type": "Split",
            "effective_date": datetime(2022, 7, 28),
            "adjustment_factor": 0.10,
            "ratio": "1:10 split",
            "source": "NSE Circular",
            "verified": True
        },
        {
            "symbol": "RELIANCE",
            "action_type": "Bonus",
            "effective_date": datetime(2017, 9, 7),
            "adjustment_factor": 0.50,
            "ratio": "1:1 bonus",
            "source": "NSE Circular",
            "verified": True
        },
        {
            "symbol": "SBIN",
            "action_type": "Split",
            "effective_date": datetime(2014, 11, 20),
            "adjustment_factor": 0.10,
            "ratio": "1:10 split",
            "source": "NSE Circular",
            "verified": True
        }
    ]
    
    async with AsyncSessionLocal() as session:
        try:
            for action_data in actions_to_seed:
                stmt = select(CorporateAction).where(
                    CorporateAction.symbol == action_data["symbol"],
                    CorporateAction.action_type == action_data["action_type"],
                    CorporateAction.effective_date == action_data["effective_date"]
                )
                res = await session.execute(stmt)
                existing = res.scalar()
                if not existing:
                    action = CorporateAction(**action_data)
                    session.add(action)
            await session.commit()
            logger.info("Corporate actions seeded successfully.")
        except Exception as e:
            await session.rollback()
            logger.error(f"Error seeding corporate actions: {e}", exc_info=True)


async def get_corporate_actions(symbol: str, db: AsyncSession) -> List[CorporateAction]:
    """Retrieve all corporate actions for a given symbol sorted by effective date ascending."""
    stmt = select(CorporateAction).where(
        CorporateAction.symbol == symbol.upper().strip()
    ).order_by(CorporateAction.effective_date.asc())
    res = await db.execute(stmt)
    return list(res.scalars().all())


def adjust_candles(df: pd.DataFrame, corporate_actions: List[CorporateAction]) -> pd.DataFrame:
    """
    Apply corporate action adjustments to a candle DataFrame.
    Adjusts OHLC prices by multiplying by the adjustment factor.
    Adjusts Volume by dividing by the adjustment factor (preserving Total Value).
    """
    if df.empty or not corporate_actions:
        return df
        
    df = df.copy()
    # Ensure temporary datetime column for safe comparisons
    df["_date_temp"] = pd.to_datetime(df["date"])
    
    adjusted_count = 0
    for action in corporate_actions:
        eff_date = pd.to_datetime(action.effective_date)
        factor = action.adjustment_factor
        
        # Candles strictly before the ex-date are adjusted
        mask = df["_date_temp"] < eff_date
        
        if mask.any():
            df.loc[mask, "open"] = df.loc[mask, "open"] * factor
            df.loc[mask, "high"] = df.loc[mask, "high"] * factor
            df.loc[mask, "low"] = df.loc[mask, "low"] * factor
            df.loc[mask, "close"] = df.loc[mask, "close"] * factor
            df.loc[mask, "volume"] = df.loc[mask, "volume"] / factor
            adjusted_count += mask.sum()
            
    if adjusted_count > 0:
        logger.info(f"Adjusted {adjusted_count} historical candles for symbol using {len(corporate_actions)} corporate action factors.")
        
    df = df.drop(columns=["_date_temp"])
    return df
