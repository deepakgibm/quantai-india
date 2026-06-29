from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from models import User, UserSettings

class UserRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        """Fetch user by primary key ID."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Fetch user by unique email address."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_username(db: AsyncSession, username: str) -> Optional[User]:
        """Fetch user by unique username."""
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(db: AsyncSession, user: User) -> User:
        """Add and flush new User object."""
        db.add(user)
        await db.flush()
        return user

    @staticmethod
    async def create_settings(db: AsyncSession, settings: UserSettings) -> UserSettings:
        """Add default user settings."""
        db.add(settings)
        return settings

    @staticmethod
    async def get_settings(db: AsyncSession, user_id: int) -> Optional[UserSettings]:
        """Fetch user settings by user ID."""
        result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
        return result.scalar_one_or_none()
