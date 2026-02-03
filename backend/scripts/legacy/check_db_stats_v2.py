import asyncio
from sqlalchemy import text
from database import get_db

async def check():
    async for db in get_db():
        res = await db.execute(text("SELECT COUNT(*) FROM instrument_master WHERE is_active = TRUE"))
        count = res.scalar()
        print(f"Active instruments: {count}")
        
        res = await db.execute(text("SELECT COUNT(*) FROM stock_candle sc JOIN instrument_master im ON sc.instrument_id = im.instrument_id WHERE im.symbol IN ('NIFTY 50', 'BANK NIFTY', 'INDIA VIX')"))
        candles = res.scalar()
        print(f"Total candles for indices: {candles}")
        
        res = await db.execute(text("SELECT im.symbol, sc.close, sc.candle_ts FROM stock_candle sc JOIN instrument_master im ON sc.instrument_id = im.instrument_id WHERE im.symbol IN ('NIFTY 50', 'BANK NIFTY', 'INDIA VIX') ORDER BY sc.candle_ts DESC LIMIT 10"))
        rows = res.fetchall()
        print("Recent index data:")
        for r in rows:
            print(r)

if __name__ == "__main__":
    asyncio.run(check())
