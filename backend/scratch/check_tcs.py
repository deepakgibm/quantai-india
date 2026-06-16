import asyncio
from database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    db = AsyncSessionLocal()
    try:
        res = await db.execute(text("SELECT symbol, is_active, instrument_key, exchange FROM instrument_master WHERE symbol='TCS'"))
        rows = res.fetchall()
        print("TCS Rows:", rows)
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(main())
