
import asyncio
from database import init_db, AsyncSessionLocal
from models import User
from utils.auth import get_password_hash
from sqlalchemy import select

async def create_user():
    await init_db()
    async with AsyncSessionLocal() as session:
        # Check if user exists
        result = await session.execute(select(User).where(User.email == "dthat@gmail.com"))
        user = result.scalar_one_or_none()
        
        if user:
            print("User already exists")
            # Update password just in case
            user.hashed_password = get_password_hash("admin123")
            await session.commit()
            print("Password updated")
        else:
            new_user = User(
                email="dthat@gmail.com",
                hashed_password=get_password_hash("admin123"),
                full_name="Admin User",
                username="admin",
                is_active=True
            )
            session.add(new_user)
            await session.commit()
            print("User created")

if __name__ == "__main__":
    asyncio.run(create_user())
