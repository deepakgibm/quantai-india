"""
Migration: Add performance indexes to stock_candle and instrument_master.

CREATE INDEX CONCURRENTLY requires running OUTSIDE a transaction block.
This script uses a raw asyncpg connection via the database URL to achieve that.

Run once:
  python backend/migrations/add_sector_analysis_indexes.py
"""

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

INDEXES = [
    {
        "name": "idx_stock_candle_timeframe_instrument_ts",
        "ddl": (
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stock_candle_timeframe_instrument_ts "
            "ON stock_candle (timeframe, instrument_id, candle_ts DESC)"
        ),
        "description": "Covering index for sector analysis CTE (timeframe + instrument_id + candle_ts)"
    },
    {
        "name": "idx_instrument_master_is_active",
        "ddl": (
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_instrument_master_is_active "
            "ON instrument_master (is_active) WHERE is_active = TRUE"
        ),
        "description": "Partial index for fast active instrument lookup"
    },
    {
        "name": "idx_fundamental_metrics_symbol",
        "ddl": (
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fundamental_metrics_symbol "
            "ON fundamental_metrics (symbol)"
        ),
        "description": "Index for LEFT JOIN between instrument_master and fundamental_metrics"
    },
]


async def run_migrations():
    try:
        import asyncpg
    except ImportError:
        logger.error("asyncpg not installed. Run: pip install asyncpg")
        return

    # Convert SQLAlchemy URL to asyncpg DSN
    db_url = settings.DATABASE_URL
    dsn = db_url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )

    conn = await asyncpg.connect(dsn)
    try:
        for idx in INDEXES:
            logger.info(f"Creating: {idx['name']} — {idx['description']}")
            try:
                await conn.execute(idx["ddl"])
                logger.info(f"  ✓ {idx['name']} created.")
            except Exception as e:
                logger.warning(f"  ⚠ {idx['name']} skipped: {e}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run_migrations())
    logger.info("Migration complete.")
