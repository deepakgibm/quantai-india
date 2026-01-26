import asyncio
import sys
import os

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from database import AsyncSessionLocal
from models import User, UserSettings
from utils.auth import get_password_hash

async def reset_user(email, password, username, full_name):
    async with AsyncSessionLocal() as db:
        try:
            # Check if user exists
            result = await db.execute(select(User).where(User.email == email))
            db_user = result.scalar_one_or_none()
            
            hashed_password = get_password_hash(password)
            
            if db_user:
                print(f"Updating existing user: {email}")
                db_user.hashed_password = hashed_password
                db_user.username = username
                db_user.full_name = full_name
                db_user.failed_login_attempts = 0
                db_user.locked_until = None
            else:
                print(f"Creating new user: {email}")
                db_user = User(
                    email=email,
                    username=username,
                    full_name=full_name,
                    hashed_password=hashed_password
                )
                db.add(db_user)
                await db.flush()
                
                # Check for settings
                res_settings = await db.execute(select(UserSettings).where(UserSettings.user_id == db_user.id))
                if not res_settings.scalar_one_or_none():
                    user_settings = UserSettings(user_id=db_user.id)
                    db.add(user_settings)
            
            await db.commit()
            print(f"Success! User {email} is ready with password: {password}")
            
        except Exception as e:
            print(f"Error: {e}")
            await db.rollback()

if __name__ == "__main__":
    email = "test_auth@quantai.com"
    password = "ValidPassword123!"
    username = "testauth"
    full_name = "Test Auth User"
    
    if len(sys.argv) > 1:
        email = sys.argv[1]
    if len(sys.argv) > 2:
        password = sys.argv[2]
    if len(sys.argv) > 3:
        username = sys.argv[3]
    if len(sys.argv) > 4:
        full_name = sys.argv[4]
        
    asyncio.run(reset_user(email, password, username, full_name))
