import asyncio
import os
import sys

# Add backend to path
sys.path.append("/app")

from database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    try:
        async with AsyncSessionLocal() as session:
            r1 = await session.execute(text("SELECT COUNT(*) FROM screener_stock_score"))
            r2 = await session.execute(text("SELECT COUNT(*) FROM screener_conviction_list"))
            r3 = await session.execute(text("SELECT MAX(score_date) FROM screener_stock_score"))
            r4 = await session.execute(text("SELECT MAX(score_date) FROM screener_conviction_list"))
            
            scores_count = r1.scalar()
            conviction_count = r2.scalar()
            max_score_date = r3.scalar()
            max_conviction_date = r4.scalar()
            
            print(f"Scores Count: {scores_count}")
            print(f"Conviction Count: {conviction_count}")
            print(f"Max Score Date: {max_score_date}")
            print(f"Max Conviction Date: {max_conviction_date}")
            
            if conviction_count > 0:
                print("\nSample Conviction Records:")
                r5 = await session.execute(text("SELECT symbol, score_date, rank, conviction_level FROM screener_conviction_list LIMIT 5"))
                for row in r5.mappings():
                    print(row)
            else:
                print("\nNo records in screener_conviction_list")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
