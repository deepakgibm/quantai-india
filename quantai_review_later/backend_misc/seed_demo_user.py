import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal, Base, engine
from models import User, UserSettings
from utils.auth import get_password_hash
from sqlalchemy import select

async def seed_demo_user():
    async with AsyncSessionLocal() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.email == "demo@example.com"))
        db_user = result.scalar_one_or_none()
        
        hashed_password = get_password_hash("demo123")
        
        if db_user:
            print("Demo user exists, updating password...")
            db_user.hashed_password = hashed_password
            await db.commit()
            print("Password updated.")
            return

        print("Creating demo user...")
        hashed_password = get_password_hash("demo123")
        db_user = User(
            email="demo@example.com",
            username="demo",
            full_name="Demo User",
            hashed_password=hashed_password,
            is_active=True
        )
        db.add(db_user)
        await db.flush()

        # Create default settings
        user_settings = UserSettings(user_id=db_user.id)
        db.add(user_settings)
        await db.commit()
        print("Demo user created successfully.")

if __name__ == "__main__":
    asyncio.run(seed_demo_user())
