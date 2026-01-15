
import asyncio
from backend.config import settings
from backend.database import get_db, init_db
from backend.models import User
from sqlalchemy import select

async def check_all():
    print(f"USING DATABASE_URL: {settings.DATABASE_URL}")
    await init_db()
    async for db in get_db():
        result = await db.execute(select(User))
        users = result.scalars().all()
        print(f"Total users found: {len(users)}")
        for u in users:
            print(f"User: {u.email}, HashLen: {len(u.hashed_password)}, Hash: {u.hashed_password}")
        break

if __name__ == "__main__":
    asyncio.run(check_all())
