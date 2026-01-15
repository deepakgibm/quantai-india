
import asyncio
from sqlalchemy import text
from database import engine, init_db, AsyncSessionLocal
from models import User
from utils.auth import get_password_hash
from sqlalchemy import select

async def fix_and_reset():
    await init_db()
    async with engine.begin() as conn:
        print("Altering column hashed_password to Text...")
        try:
            await conn.execute(text("ALTER TABLE users ALTER COLUMN hashed_password TYPE TEXT"))
            print("Column altered successfully")
        except Exception as e:
            print(f"Altering failed (maybe already fixed or SQLite): {e}")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == "dthat@gmail.com"))
        user = result.scalar_one_or_none()
        if user:
            new_hash = get_password_hash("admin123")
            print(f"Setting new hash: {new_hash}")
            user.hashed_password = new_hash
            await session.commit()
            print("Password reset successfully")
            
            # Verify length
            print(f"Stored hash length: {len(user.hashed_password)}")
        else:
            print("User not found to reset")

if __name__ == "__main__":
    asyncio.run(fix_and_reset())
