import asyncio
import sys
sys.path.insert(0, '.')

from database import AsyncSessionLocal
from models import User, UserSettings
from utils.auth import get_password_hash
from sqlalchemy import select

async def test_signup():
    try:
        async with AsyncSessionLocal() as db:
            # Check if user exists
            result = await db.execute(select(User).where(User.email == "testscript@test.com"))
            existing = result.scalar_one_or_none()
            if existing:
                print("User already exists")
                return
            
            # Create user
            db_user = User(
                email="testscript@test.com",
                username="testscript",
                full_name="Test Script User",
                hashed_password=get_password_hash("test123")
            )
            db.add(db_user)
            await db.flush()
            print(f"User created with ID: {db_user.id}")
            
            # Create default settings
            user_settings = UserSettings(user_id=db_user.id)
            db.add(user_settings)
            await db.commit()
            print("Settings created")
            
            await db.refresh(db_user)
            print(f"Signup successful! User: {db_user.email}")
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_signup())
