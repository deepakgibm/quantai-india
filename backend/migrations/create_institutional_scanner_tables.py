import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
import os
import sys

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from config import settings
from database import Base

async def create_tables():
    print("Connecting to database at:", settings.DATABASE_URL)
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Institutional Scanner tables verified/created successfully.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_tables())
