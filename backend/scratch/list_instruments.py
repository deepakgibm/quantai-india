import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as session:
        r = await session.execute(text("SELECT symbol, company_name, exchange, sector, instrument_key FROM instrument_master LIMIT 10"))
        for row in r.all():
            print(row)

if __name__ == "__main__":
    asyncio.run(check())
