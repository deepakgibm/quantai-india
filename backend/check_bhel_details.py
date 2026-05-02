import asyncio
import sys
sys.path.append("/app")
from database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as session:
        r = await session.execute(text("SELECT symbol, promoter_score, institutional_score, earnings_score, debt_score, technical_score, overall_score, conviction_level FROM screener_stock_score WHERE symbol = 'BHEL' ORDER BY score_date DESC LIMIT 1"))
        row = r.mappings().fetchone()
        if row:
            print(f"BHEL: {row}")
        else:
            print("BHEL not found")

if __name__ == "__main__":
    asyncio.run(check())
