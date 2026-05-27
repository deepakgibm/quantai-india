import asyncio
from sqlalchemy import text
from database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as session:
        query = text("""
            SELECT symbol, instrument_key, exchange, is_active 
            FROM instrument_master 
            WHERE symbol = 'RELIANCE'
            LIMIT 5;
        """)
        result = await session.execute(query)
        rows = result.fetchall()
        print(f"Found {len(rows)} entries for RELIANCE:")
        for r in rows:
            print(f" - {r.symbol}: Key={r.instrument_key}, Exchange={r.exchange}, Active={r.is_active}")

if __name__ == "__main__":
    asyncio.run(main())
