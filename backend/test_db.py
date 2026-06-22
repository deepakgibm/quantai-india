import asyncio
import logging
from sqlalchemy import text
from database import AsyncSessionLocal

logging.basicConfig(level=logging.INFO)

async def test_db():
    async with AsyncSessionLocal() as session:
        for sym in ["NIFTY 50", "BANK NIFTY", "INDIA VIX"]:
            res = await session.execute(
                text("SELECT sc.close, sc.candle_ts, im.symbol FROM stock_candle sc JOIN instrument_master im ON sc.instrument_id = im.instrument_id WHERE im.symbol = :sym AND sc.timeframe = 1440 ORDER BY sc.candle_ts DESC LIMIT 2"),
                {"sym": sym}
            )
            rows = res.fetchall()
            print(f"Query result for {sym}:", rows)

if __name__ == "__main__":
    asyncio.run(test_db())
