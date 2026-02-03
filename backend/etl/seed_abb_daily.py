import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# Ensure project root is on PYTHONPATH for imports
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from database import AsyncSessionLocal
from models_alpha import StockCandle, InstrumentMaster
from sqlalchemy import select

async def seed_abb():
    async with AsyncSessionLocal() as session:
        # Get ABB ID
        stmt = select(InstrumentMaster).where(InstrumentMaster.symbol == "ABB")
        result = await session.execute(stmt)
        abb = result.scalar_one_or_none()
        
        if not abb:
            print("ABB not found in InstrumentMaster")
            return

        print(f"Seeding data for ABB (ID: {abb.instrument_id})")
        
        # Generate 60 days of data
        end_date = datetime.now()
        price = 5000.0
        
        candles = []
        for i in range(100):
            date = end_date - timedelta(days=100-i)
            # Skip weekends logic skipped for simplicity, just linear
            
            open_p = price
            close_p = price * (1 + random.uniform(-0.02, 0.02))
            high_p = max(open_p, close_p) * 1.01
            low_p = min(open_p, close_p) * 0.99
            
            candle = StockCandle(
                instrument_id=abb.instrument_id,
                timeframe=1440, # Daily
                candle_ts=date,
                open=open_p,
                high=high_p,
                low=low_p,
                close=close_p,
                volume=random.randint(1000, 100000)
            )
            candles.append(candle)
            price = close_p
            
        session.add_all(candles)
        await session.commit()
        print(f"Preserved {len(candles)} candles.")

if __name__ == "__main__":
    asyncio.run(seed_abb())
