
import asyncio
import bcrypt
from database import init_db, AsyncSessionLocal
from models import User
from sqlalchemy import select

async def fix_and_reset():
    await init_db()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == "dthat@gmail.com"))
        user = result.scalar_one_or_none()
        if user:
            # Use bcrypt directly
            pw = "admin123"
            new_hash = bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')
            print(f"Generated hash: {new_hash}")
            print(f"Length: {len(new_hash)}")
            
            user.hashed_password = new_hash
            await session.commit()
            print("Password reset successfully")
            
            # Re-read to confirm
            await session.refresh(user)
            print(f"Stored hash: {user.hashed_password}")
            print(f"Stored length: {len(user.hashed_password)}")
        else:
            print("User not found")

if __name__ == "__main__":
    asyncio.run(fix_and_reset())
