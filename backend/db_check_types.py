import asyncio
import sys
sys.path.append("/app")
from database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as session:
        r = await session.execute(text("SELECT list_type, COUNT(*) FROM screener_conviction_list WHERE score_date = '2026-04-22' GROUP BY list_type"))
        for row in r.all():
            print(f"List Type: {row[0]}, Count: {row[1]}")

if __name__ == "__main__":
    asyncio.run(check())
