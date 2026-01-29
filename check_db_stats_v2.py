import asyncio
from sqlalchemy import text
from database import get_db

async def check():
    async for db in get_db():
        res = await db.execute(text("SELECT COUNT(*) FROM instrument_master WHERE is_active = TRUE"))
        count = res.scalar()
        print(f"Active instruments: {count}")
        
        res = await db.execute(text("SELECT COUNT(*) FROM stock_candle"))
        candles = res.scalar()
        print(f"Total candles: {candles}")

if __name__ == "__main__":
    asyncio.run(check())
