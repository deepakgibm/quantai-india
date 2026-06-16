import asyncio
import sys
import os
from sqlalchemy import text

# Add parent directory of scratch to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import AsyncSessionLocal

async def test():
    async with AsyncSessionLocal() as session:
        r = await session.execute(text("SELECT COUNT(DISTINCT instrument_id) FROM stock_candle WHERE timeframe = 1440"))
        print("Distinct instruments with daily candles:", r.scalar())
        
        # Also let's print a sample of symbols with candles
        r2 = await session.execute(text("""
            SELECT DISTINCT im.symbol 
            FROM stock_candle sc 
            JOIN instrument_master im ON sc.instrument_id = im.instrument_id 
            WHERE sc.timeframe = 1440 
            LIMIT 20
        """))
        print("Sample symbols with candles:", [row[0] for row in r2.fetchall()])

if __name__ == "__main__":
    asyncio.run(test())
