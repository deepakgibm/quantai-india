import asyncio
import sys
sys.path.append('.')

from database import AsyncSessionLocal, init_db
from models import User, UserSettings
from utils.auth import get_password_hash
from sqlalchemy import select

async def create_user():
    await init_db()
    
    async with AsyncSessionLocal() as session:
        # Check if user exists
        result = await session.execute(select(User).where(User.email == "demo@example.com"))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"User exists: {existing_user.email}")
            # Update password
            existing_user.hashed_password = get_password_hash("demo123")
            await session.commit()
            print("✅ Password updated to: demo123")
        else:
            # Create new user
            user = User(
                email="demo@example.com",
                username="demo",
                hashed_password=get_password_hash("demo123"),
                full_name="Demo User",
                is_active=True
            )
            session.add(user)
            await session.flush()
            
            # Create settings
            settings = UserSettings(user_id=user.id)
            session.add(settings)
            await session.commit()
            print("✅ Created demo user")
            print(f"   Email: demo@example.com")
            print(f"   Password: demo123")

if __name__ == "__main__":
    asyncio.run(create_user())
