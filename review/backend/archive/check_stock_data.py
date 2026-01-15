import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import sys
import os

database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:admin@localhost:5432/quantai")

async def check_stock_data():
    try:
        engine = create_async_engine(database_url)
        print(f"Connecting to {database_url}...")
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM stock_data"))
            count = result.scalar()
            print(f"Total rows in stock_data: {count}")
            
            result = await conn.execute(text("SELECT DISTINCT symbol FROM stock_data LIMIT 10"))
            symbols = [row[0] for row in result.fetchall()]
            print(f"Sample symbols: {symbols}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_stock_data())
