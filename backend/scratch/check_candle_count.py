import asyncio
from sqlalchemy import text
from database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as session:
        query = text("""
            SELECT im.symbol, count(*) as count, min(sc.candle_ts) as min_ts, max(sc.candle_ts) as max_ts
            FROM stock_candle sc 
            JOIN instrument_master im ON sc.instrument_id = im.instrument_id 
            WHERE sc.timeframe = 1440 
            GROUP BY im.symbol
            LIMIT 10;
        """)
        result = await session.execute(query)
        rows = result.fetchall()
        print("Candle counts by symbol:")
        for r in rows:
            print(f" - {r.symbol}: Count={r.count}, Min={r.min_ts}, Max={r.max_ts}")

if __name__ == "__main__":
    asyncio.run(main())
