import asyncio
import os
from sqlalchemy import text
from database import AsyncSessionLocal

async def check_counts():
    async with AsyncSessionLocal() as session:
        # Check 15m candles for a few symbols
        symbols = ["RELIANCE", "TCS", "ACC"]
        for sym in symbols:
            query = text("""
                SELECT COUNT(*) 
                FROM stock_candle sc 
                JOIN instrument_master im ON sc.instrument_id = im.instrument_id 
                WHERE im.symbol = :sym AND sc.timeframe = 15
            """)
            result = await session.execute(query, {"sym": sym})
            count = result.scalar()
            print(f"{sym} (15m): {count} candles")
            
            # Also check last timestamp
            query_ts = text("""
                SELECT MAX(candle_ts) 
                FROM stock_candle sc 
                JOIN instrument_master im ON sc.instrument_id = im.instrument_id 
                WHERE im.symbol = :sym AND sc.timeframe = 15
            """)
            result_ts = await session.execute(query_ts, {"sym": sym})
            last_ts = result_ts.scalar()
            print(f"{sym} (15m) Last: {last_ts}")

if __name__ == "__main__":
    asyncio.run(check_counts())
