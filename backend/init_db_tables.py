import asyncio
from database import engine, Base

async def sync_db():
    print("?? Synchronizing database schema with models...")
    async with engine.begin() as conn:
        # This will create tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)
    print("?? Schema sync complete.")

if __name__ == "__main__":
    asyncio.run(sync_db())
