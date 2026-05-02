import asyncio
import sys
sys.path.append("/app")
from database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as session:
        r = await session.execute(text("SELECT COUNT(*) FROM screener_conviction_list WHERE score_date = '2026-04-22'"))
        count = r.scalar()
        print(f"Count for 2026-04-22: {count}")
        
        r2 = await session.execute(text("SELECT DISTINCT score_date FROM screener_conviction_list ORDER BY score_date DESC"))
        print("Dates in conviction list:")
        for row in r2.all():
            print(row[0])

if __name__ == "__main__":
    asyncio.run(check())
