
import asyncio
from database import AsyncSessionLocal
from sqlalchemy import text

async def check_index_schema():
    async with AsyncSessionLocal() as session:
        # Check if we have any NIFTY 50 or similar
        query = text("""
            SELECT instrument_id, symbol, exchange, segment, series, instrument_key 
            FROM instrument_master 
            WHERE symbol LIKE 'NIFTY%' OR symbol LIKE 'INDIA VIX'
            LIMIT 10
        """)
        result = await session.execute(query)
        rows = result.fetchall()
        print(f"Found {len(rows)} potential index rows:")
        for row in rows:
            print(row)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(check_index_schema())
