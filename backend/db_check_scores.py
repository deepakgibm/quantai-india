import asyncio
import sys
sys.path.append("/app")
from database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as session:
        r = await session.execute(text("SELECT MIN(overall_score), MAX(overall_score), AVG(overall_score) FROM screener_stock_score WHERE score_date = '2026-04-22'"))
        row = r.fetchone()
        print(f"Scores for 2026-04-22: Min: {row[0]}, Max: {row[1]}, Avg: {row[2]}")
        
        r2 = await session.execute(text("SELECT conviction_level, COUNT(*) FROM screener_stock_score WHERE score_date = '2026-04-22' GROUP BY conviction_level"))
        print("\nConviction Levels for 2026-04-22:")
        for row in r2.all():
            print(f"Level: {row[0]}, Count: {row[1]}")

if __name__ == "__main__":
    asyncio.run(check())
