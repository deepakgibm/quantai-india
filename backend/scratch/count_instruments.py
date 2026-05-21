import asyncio
import sys
from pathlib import Path

# Add backend directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as session:
        r = await session.execute(text("SELECT count(*), count(distinct symbol), count(*) FILTER (WHERE is_active = TRUE) FROM instrument_master"))
        print("Count results:", r.all())

if __name__ == "__main__":
    asyncio.run(check())
