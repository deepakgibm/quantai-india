import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Use connection string from env or fallback
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@quantai-db:5432/quantai")

async def check():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        # Check users table
        print("--- USERS TABLE ---")
        try:
            result = await conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'users' ORDER BY column_name"))
            rows = result.fetchall()
            if not rows:
                print("Table 'users' NOT FOUND!")
            for row in rows:
                print(f"{row[0]}: {row[1]}")
        except Exception as e:
            print(f"Error checking users table: {e}")

        # Check user_settings table
        print("\n--- USER_SETTINGS TABLE ---")
        try:
            result = await conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'user_settings' ORDER BY column_name"))
            rows = result.fetchall()
            if not rows:
                print("Table 'user_settings' NOT FOUND!")
            for row in rows:
                print(f"{row[0]}: {row[1]}")
        except Exception as e:
            print(f"Error checking user_settings table: {e}")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
