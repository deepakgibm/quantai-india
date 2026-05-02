import asyncio
import sys
sys.path.append("/app")
from database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as session:
        r = await session.execute(text("SELECT symbol, overall_score, score_breakdown FROM screener_stock_score WHERE score_date = '2026-04-22' LIMIT 3"))
        for row in r.mappings():
            print(f"Symbol: {row['symbol']}, Overall: {row['overall_score']}")
            print(f"Breakdown: {row['score_breakdown']}")
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(check())
