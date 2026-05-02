import asyncio
import sys
sys.path.append("/app")
from database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as session:
        r = await session.execute(text("SELECT symbol FROM instrument_master WHERE is_active = TRUE AND exchange = 'NSE' AND series IN ('EQ', 'INDEX') ORDER BY symbol LIMIT 100"))
        print([row[0] for row in r.all()])

if __name__ == "__main__":
    asyncio.run(check())
