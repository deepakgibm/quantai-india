from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

# Create async engine - works with both PostgreSQL and SQLite
engine = create_async_engine(
    settings.DATABASE_URL, 
    echo=False,
    # PostgreSQL-specific settings
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Check connection health before using
)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
