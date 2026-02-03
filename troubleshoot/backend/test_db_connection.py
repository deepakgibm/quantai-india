import asyncio
from database import AsyncSessionLocal
from sqlalchemy import text

async def test():
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            print("Async DB OK")
    except Exception as e:
        print(f"DB Error: {e}")

asyncio.run(test())
