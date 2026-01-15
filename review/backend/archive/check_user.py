
import asyncio
from sqlalchemy import select
from database import get_db, init_db
from models import User

async def check_user():
    await init_db()
    async for db in get_db():
        result = await db.execute(select(User).where(User.email == "dthat@gmail.com"))
        user = result.scalar_one_or_none()
        if user:
            print(f"User found: {user.email}")
            print(f"Username: {user.username}")
            print(f"Hashed Password: {user.hashed_password}")
        else:
            print("User not found: dthat@gmail.com")
        break

if __name__ == "__main__":
    asyncio.run(check_user())
