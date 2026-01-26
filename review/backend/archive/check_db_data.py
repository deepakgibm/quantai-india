import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os

database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:admin@localhost:5432/quantai")

async def check_data():
    try:
        engine = create_async_engine(database_url)
        async with engine.connect() as conn:
            # Check for tables
            result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = [row[0] for row in result.fetchall()]
            print(f"Tables in DB: {tables}")
            
            for table in tables:
                res = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = res.scalar()
                print(f"Table {table}: {count} rows")
                
    except Exception as e:
        print(f"Error checking data: {e}")

if __name__ == "__main__":
    asyncio.run(check_data())
