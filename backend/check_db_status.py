
import asyncio
from sqlalchemy import text
from database import AsyncSessionLocal

async def check_db():
    async with AsyncSessionLocal() as session:
        # Check stock_candles (legacy)
        try:
            res = await session.execute(text("SELECT timeframe, COUNT(*) FROM stock_candles GROUP BY timeframe"))
            print("Legacy table (stock_candles):")
            for row in res.all():
                print(f"  {row[0]}: {row[1]} rows")
        except Exception as e:
            print(f"Error checking stock_candles: {e}")

        # Check stock_candle (v2)
        try:
            res = await session.execute(text("SELECT timeframe, COUNT(*) FROM stock_candle GROUP BY timeframe"))
            print("V2 table (stock_candle):")
            for row in res.all():
                print(f"  {row[0]} min: {row[1]} rows")
        except Exception as e:
            print(f"Error checking stock_candle: {e}")

        # Check instrument_master
        try:
            res = await session.execute(text("SELECT COUNT(*) FROM instrument_master"))
            print(f"InstrumentMaster: {res.scalar()} rows")
        except Exception as e:
            print(f"Error checking instrument_master: {e}")

if __name__ == "__main__":
    asyncio.run(check_db())
