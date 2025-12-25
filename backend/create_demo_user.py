"""
Create Demo User Script
Run this to create a demo user for testing.
"""
import asyncio
import sys
sys.path.insert(0, '.')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

from config import settings
from models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_demo_user():
    """Create demo user if it doesn't exist."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check if demo user exists
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.email == "demo@example.com")
        )
        existing_user = result.scalars().first()
        
        if existing_user:
            print("✓ Demo user already exists")
            print(f"  Email: {existing_user.email}")
            return
        
        # Create demo user
        demo_user = User(
            email="demo@example.com",
            hashed_password=pwd_context.hash("demo123"),
            full_name="Demo Trader",
            is_active=True
        )
        
        session.add(demo_user)
        await session.commit()
        
        print("✓ Demo user created successfully!")
        print("  Email: demo@example.com")
        print("  Password: demo123")

if __name__ == "__main__":
    asyncio.run(create_demo_user())
