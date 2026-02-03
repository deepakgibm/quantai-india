import asyncio
from sqlalchemy import text
from database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as session:
        query = text("""
            SELECT im.symbol, sc.close, sc.candle_ts, sc.timeframe 
            FROM stock_candle sc 
            JOIN instrument_master im ON sc.instrument_id = im.instrument_id 
            WHERE im.symbol = 'ABB' AND sc.timeframe = 1440 
            ORDER BY sc.candle_ts DESC 
            LIMIT 5;
        """)
        result = await session.execute(query)
        rows = result.fetchall()
        print(f"Found {len(rows)} daily candles for ABB:")
        for r in rows:
            print(f" - {r.symbol}: Close={r.close}, TS={r.candle_ts}")

if __name__ == "__main__":
    asyncio.run(main())
