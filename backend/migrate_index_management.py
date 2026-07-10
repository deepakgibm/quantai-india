"""
Migration: Add Index Management Columns
Run inside backend docker container: python migrate_index_management.py
"""
from sqlalchemy import create_engine, text
from config import settings

engine = create_engine(settings.SYNC_DATABASE_URL)

MIGRATIONS = [
    # Extend index_master
    "ALTER TABLE index_master ALTER COLUMN index_name TYPE VARCHAR(100)",
    "ALTER TABLE index_master ADD COLUMN IF NOT EXISTS display_name VARCHAR(100)",
    "ALTER TABLE index_master ADD COLUMN IF NOT EXISTS category VARCHAR(50)",
    "ALTER TABLE index_master ADD COLUMN IF NOT EXISTS nse_index_code VARCHAR(100)",
    "ALTER TABLE index_master ADD COLUMN IF NOT EXISTS csv_url TEXT",
    "ALTER TABLE index_master ADD COLUMN IF NOT EXISTS last_refreshed TIMESTAMP",
    "ALTER TABLE index_master ADD COLUMN IF NOT EXISTS constituent_count INTEGER DEFAULT 0",
    "ALTER TABLE index_master ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()",
    # Extend index_constituent
    "ALTER TABLE index_constituent ADD COLUMN IF NOT EXISTS sector VARCHAR(100)",
    "ALTER TABLE index_constituent ADD COLUMN IF NOT EXISTS industry VARCHAR(100)",
    "ALTER TABLE index_constituent ADD COLUMN IF NOT EXISTS removed_at TIMESTAMP",
    # Create index_refresh_log
    """CREATE TABLE IF NOT EXISTS index_refresh_log (
        id SERIAL PRIMARY KEY,
        index_id INTEGER REFERENCES index_master(index_id) ON DELETE SET NULL,
        index_name VARCHAR(100),
        refreshed_at TIMESTAMP DEFAULT NOW(),
        added_count INTEGER DEFAULT 0,
        removed_count INTEGER DEFAULT 0,
        matched_count INTEGER DEFAULT 0,
        missing_count INTEGER DEFAULT 0,
        total_nse_count INTEGER DEFAULT 0,
        coverage_pct FLOAT DEFAULT 0.0,
        status VARCHAR(20) DEFAULT 'success',
        error_message TEXT,
        missing_symbols TEXT
    )""",
]

with engine.begin() as conn:
    for stmt in MIGRATIONS:
        label = stmt.strip()[:70].replace('\n', ' ')
        try:
            conn.execute(text(stmt))
            print(f"  OK  : {label}")
        except Exception as e:
            print(f"  SKIP: {label} => {e}")

print("\nMigration complete.")
