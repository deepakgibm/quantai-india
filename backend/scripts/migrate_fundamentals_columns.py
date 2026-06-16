import asyncio
import sys
import os
from sqlalchemy import text

# Add parent directory of scripts to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import AsyncSessionLocal

async def migrate():
    print("[MIGRATION] Adding sector PE/PB benchmark columns to fundamental_metrics...")
    async with AsyncSessionLocal() as session:
        try:
            # PostgreSQL syntax
            await session.execute(text("ALTER TABLE fundamental_metrics ADD COLUMN IF NOT EXISTS sector_pe_benchmark FLOAT"))
            await session.execute(text("ALTER TABLE fundamental_metrics ADD COLUMN IF NOT EXISTS sector_pb_benchmark FLOAT"))
            await session.commit()
            print("[MIGRATION] Migration successful!")
        except Exception as e:
            await session.rollback()
            print("[MIGRATION] Migration failed:", e)

if __name__ == "__main__":
    asyncio.run(migrate())
