
import asyncio
from database import AsyncSessionLocal
from sqlalchemy import text

async def check_instruments():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT instrument_id, symbol, name FROM instrument_master WHERE symbol IN ('NIFTY 50', 'BANK NIFTY', 'INDIA VIX')"))
        rows = result.fetchall()
        print(f"Found {len(rows)} indices:")
        for row in rows:
            print(row)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(check_instruments())
