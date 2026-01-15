import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import sys
import os

# Try to load .env manually if needed, but here we can just hardcode or read from environment
database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:admin@localhost:5432/quantai")

async def test_conn():
    print(f"Testing connection to: {database_url}")
    try:
        engine = create_async_engine(database_url)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("Connection successful!")
            print(f"Result: {result.fetchone()}")
    except Exception as e:
        print(f"Connection failed: {e}")
        # Check if SQLite file exists
        if os.path.exists("quantai.db"):
            print("quantai.db exists locally.")
        else:
            print("quantai.db not found.")

if __name__ == "__main__":
    asyncio.run(test_conn())
