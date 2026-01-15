"""
Database migration to create scanner_presets table.
Run this script once to create the missing table.
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from config import settings

async def create_scanner_presets_table():
    """Create scanner_presets table if it doesn't exist."""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS scanner_presets (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        name VARCHAR(255) NOT NULL,
        indices JSONB,
        timeframe VARCHAR(50),
        strategies JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX IF NOT EXISTS idx_scanner_presets_user_id ON scanner_presets(user_id);
    """
    
    async with engine.begin() as conn:
        await conn.execute(text(create_table_sql))
        print("✅ scanner_presets table created successfully")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_scanner_presets_table())
