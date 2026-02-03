import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test():
    db_url = os.getenv('DATABASE_URL')
    print(f"Testing connection to: {db_url}")
    try:
        engine = create_async_engine(db_url)
        print("Engine created. Connecting...")
        async with engine.connect() as conn:
            print("Connected. Executing query...")
            await conn.execute(text("SELECT 1"))
            print("DB Success!")
            
            print("Checking for user table and user...")
            result = await conn.execute(text("SELECT * FROM users WHERE email='dthat53@gmail.com'"))
            user = result.fetchone()
            if user:
                print(f"User found: {user}")
            else:
                print("User NOT found!")
    except Exception as e:
        print(f"DB Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
