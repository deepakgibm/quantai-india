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
            "screener_bulk_deals",
            "institutional_flows"
        ]
        for table in tables:
            try:
                r = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                print(f"{table}: {r.scalar()}")
            except Exception as e:
                print(f"{table}: Table not found or error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
