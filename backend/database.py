from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.types import TypeDecorator, String
from config import settings
from core.security import encrypt_token, decrypt_token

# Create async engines
# Write engine (Primary)
engine = create_async_engine(
    settings.DATABASE_URL, 
    echo=False,
    pool_size=10 if not settings.PGBOUNCER_ENABLED else 0,
    max_overflow=20 if not settings.PGBOUNCER_ENABLED else 0,
    pool_pre_ping=True,
)

# Read engine (Replica)
read_engine = create_async_engine(
    settings.READ_DATABASE_URL,
    echo=False,
    pool_size=10 if not settings.PGBOUNCER_ENABLED else 0,
    max_overflow=20 if not settings.PGBOUNCER_ENABLED else 0,
    pool_pre_ping=True,
)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
AsyncReadSessionLocal = sessionmaker(read_engine, class_=AsyncSession, expire_on_commit=False)

class EncryptedString(TypeDecorator):
    """
    SQLAlchemy TypeDecorator that transparently encrypts and decrypts string values
    using the application's TOKEN_ENCRYPTION_KEY.
    """
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return encrypt_token(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                return decrypt_token(value)
            except Exception:
                # Fallback for plain-text legacy data or corrupt values during migration
                return value
        return value

Base = declarative_base()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def verify_database_health():
    """
    Perform a complete database health check:
    - Ping (write engine)
    - Ping (read engine)
    - Write test
    - Read test
    - Transaction test
    Fails (raises exception) if database is unavailable or behaving incorrectly.
    """
    import logging
    from sqlalchemy import text
    logger = logging.getLogger(__name__)
    logger.info("Performing database health check (Ping, Read, Write, Transaction)...")
    
    # 1. Ping write engine
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database write engine ping failed: {e}")
        raise RuntimeError(f"Database write engine ping failed: {e}")

    # 2. Ping read engine
    try:
        async with read_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database read engine ping failed: {e}")
        raise RuntimeError(f"Database read engine ping failed: {e}")

    # 3. Write, Read, and Transaction test
    try:
        async with engine.connect() as conn:
            trans = await conn.begin()
            try:
                await conn.execute(text("CREATE TEMP TABLE db_health_check_test (id SERIAL PRIMARY KEY, val VARCHAR(50))"))
                await conn.execute(text("INSERT INTO db_health_check_test (val) VALUES ('quantai_ok')"))
                res = await conn.execute(text("SELECT val FROM db_health_check_test"))
                val = res.scalar()
                if val != 'quantai_ok':
                    raise ValueError(f"Value read back '{val}' did not match written 'quantai_ok'")
                await trans.rollback()
            except Exception as e:
                await trans.rollback()
                raise e
    except Exception as e:
        logger.error(f"Database write/read/transaction verification failed: {e}")
        raise RuntimeError(f"Database write/read/transaction verification failed: {e}")
        
    logger.info("Database health check completed successfully.")

async def get_db():
    """Dependency for write sessions (Primary)."""
    async with AsyncSessionLocal() as session:
        yield session

async def get_read_db():
    """Dependency for read sessions (Replica)."""
    async with AsyncReadSessionLocal() as session:
        yield session

from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db_session_context():
    """Async context manager for DB sessions, used by background services."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Sync DB Connection (for legacy services & Celery)
from sqlalchemy import create_engine
sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    pool_size=10 if not settings.PGBOUNCER_ENABLED else 0,
    max_overflow=20 if not settings.PGBOUNCER_ENABLED else 0,
    pool_pre_ping=True
)

sync_read_engine = create_engine(
    settings.SYNC_READ_DATABASE_URL,
    pool_size=10 if not settings.PGBOUNCER_ENABLED else 0,
    max_overflow=20 if not settings.PGBOUNCER_ENABLED else 0,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
ReadSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_read_engine)
