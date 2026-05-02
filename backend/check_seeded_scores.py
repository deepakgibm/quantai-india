import asyncio
import sys
sys.path.append("/app")
from database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as session:
        r = await session.execute(text("SELECT symbol, overall_score, conviction_level FROM screener_stock_score WHERE symbol IN ('BHEL', 'RELIANCE', 'TCS') ORDER BY score_date DESC"))
        for row in r.all():
            print(f"Symbol: {row[0]}, Score: {row[1]}, Conviction: {row[2]}")

if __name__ == "__main__":
    asyncio.run(check())
