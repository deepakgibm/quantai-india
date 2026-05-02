import asyncio
import sys
sys.path.append("/app")
from database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as session:
        tables = [
            "screener_financials",
            "screener_holdings_history",
            "screener_insider_activity",
            "screener_bulk_deals",
            "instrument_master"
        ]
        for table in tables:
            r = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            print(f"{table}: {r.scalar()}")

if __name__ == "__main__":
    asyncio.run(check())
