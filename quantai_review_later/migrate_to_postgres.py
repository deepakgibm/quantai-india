"""
SQLite to PostgreSQL Migration Script
Transfers all data from quantai.db (SQLite) to PostgreSQL.
"""

import sqlite3
import psycopg2
from psycopg2.extras import execute_batch
import time
from datetime import datetime

# Connection settings
SQLITE_PATH = "quantai.db"
PG_HOST = "localhost"
PG_PORT = 5432
PG_USER = "postgres"
PG_PASSWORD = "admin"
PG_DATABASE = "quantai"

# Batch size for data transfer (larger = faster but uses more memory)
BATCH_SIZE = 10000


def get_sqlite_tables(sqlite_conn):
    """Get all table names from SQLite database."""
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return [row[0] for row in cursor.fetchall()]


def get_table_schema(sqlite_conn, table_name):
    """Get column info for a table."""
    cursor = sqlite_conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return cursor.fetchall()


def get_row_count(sqlite_conn, table_name):
    """Get row count for a table."""
    cursor = sqlite_conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    return cursor.fetchone()[0]


def sqlite_to_pg_type(sqlite_type):
    """Convert SQLite type to PostgreSQL type."""
    sqlite_type = (sqlite_type or "TEXT").upper()
    if "INT" in sqlite_type:
        return "INTEGER"
    elif "CHAR" in sqlite_type or "CLOB" in sqlite_type or "TEXT" in sqlite_type:
        return "TEXT"
    elif "BLOB" in sqlite_type:
        return "BYTEA"
    elif "REAL" in sqlite_type or "FLOA" in sqlite_type or "DOUB" in sqlite_type:
        return "DOUBLE PRECISION"
    elif "BOOL" in sqlite_type:
        return "BOOLEAN"
    elif "DATE" in sqlite_type or "TIME" in sqlite_type:
        return "TIMESTAMP"
    else:
        return "TEXT"


def create_table_in_postgres(pg_conn, table_name, schema):
    """Create table in PostgreSQL based on SQLite schema."""
    columns = []
    for col in schema:
        col_id, col_name, col_type, not_null, default_val, is_pk = col
        pg_type = sqlite_to_pg_type(col_type)
        
        col_def = f'"{col_name}" {pg_type}'
        if is_pk:
            col_def = f'"{col_name}" SERIAL PRIMARY KEY' if pg_type == "INTEGER" else f'"{col_name}" {pg_type} PRIMARY KEY'
        elif not_null:
            col_def += " NOT NULL"
        columns.append(col_def)
    
    create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(columns)})'
    
    cursor = pg_conn.cursor()
    try:
        cursor.execute(create_sql)
        pg_conn.commit()
        print(f"  Created table: {table_name}")
    except Exception as e:
        pg_conn.rollback()
        print(f"  Warning creating {table_name}: {e}")


def migrate_table_data(sqlite_conn, pg_conn, table_name, schema):
    """Migrate data from SQLite table to PostgreSQL."""
    row_count = get_row_count(sqlite_conn, table_name)
    if row_count == 0:
        print(f"  {table_name}: No data to migrate")
        return 0
    
    columns = [col[1] for col in schema]
    col_list = ", ".join([f'"{c}"' for c in columns])
    placeholders = ", ".join(["%s"] * len(columns))
    
    insert_sql = f'INSERT INTO "{table_name}" ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
    
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()
    
    migrated = 0
    start_time = time.time()
    
    # Use generator to stream rows
    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
    
    batch = []
    for row in sqlite_cursor:
        # Convert None and handle special types
        converted_row = []
        for i, val in enumerate(row):
            if val is None:
                converted_row.append(None)
            elif isinstance(val, bytes):
                converted_row.append(psycopg2.Binary(val))
            else:
                converted_row.append(val)
        batch.append(tuple(converted_row))
        
        if len(batch) >= BATCH_SIZE:
            try:
                execute_batch(pg_cursor, insert_sql, batch, page_size=1000)
                pg_conn.commit()
                migrated += len(batch)
                elapsed = time.time() - start_time
                rate = migrated / elapsed if elapsed > 0 else 0
                print(f"  {table_name}: {migrated:,}/{row_count:,} ({migrated*100//row_count}%) - {rate:.0f} rows/sec", end="\r")
            except Exception as e:
                pg_conn.rollback()
                print(f"\n  Error in batch: {e}")
            batch = []
    
    # Final batch
    if batch:
        try:
            execute_batch(pg_cursor, insert_sql, batch, page_size=1000)
            pg_conn.commit()
            migrated += len(batch)
        except Exception as e:
            pg_conn.rollback()
            print(f"\n  Error in final batch: {e}")
    
    elapsed = time.time() - start_time
    print(f"\n  {table_name}: Migrated {migrated:,} rows in {elapsed:.1f}s")
    return migrated


def main():
    print("=" * 60)
    print("SQLite to PostgreSQL Migration")
    print("=" * 60)
    print(f"Source: {SQLITE_PATH}")
    print(f"Target: postgres://{PG_USER}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}")
    print()
    
    # Connect to SQLite
    print("Connecting to SQLite...")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    
    # Connect to PostgreSQL
    print("Connecting to PostgreSQL...")
    pg_conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        password=PG_PASSWORD,
        database=PG_DATABASE
    )
    
    # Get tables
    tables = get_sqlite_tables(sqlite_conn)
    print(f"\nFound {len(tables)} tables to migrate:")
    for t in tables:
        count = get_row_count(sqlite_conn, t)
        print(f"  - {t}: {count:,} rows")
    
    print("\n" + "=" * 60)
    print("Phase 1: Creating Tables in PostgreSQL")
    print("=" * 60)
    
    for table_name in tables:
        schema = get_table_schema(sqlite_conn, table_name)
        create_table_in_postgres(pg_conn, table_name, schema)
    
    print("\n" + "=" * 60)
    print("Phase 2: Migrating Data")
    print("=" * 60)
    
    total_migrated = 0
    start_total = time.time()
    
    # Migrate smaller tables first, leave stock_data for last
    priority_order = sorted(tables, key=lambda t: get_row_count(sqlite_conn, t))
    
    for table_name in priority_order:
        schema = get_table_schema(sqlite_conn, table_name)
        migrated = migrate_table_data(sqlite_conn, pg_conn, table_name, schema)
        total_migrated += migrated
    
    total_time = time.time() - start_total
    
    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print(f"Total rows migrated: {total_migrated:,}")
    print(f"Total time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
    
    # Cleanup
    sqlite_conn.close()
    pg_conn.close()
    
    print("\nNext steps:")
    print("1. Restart the backend server")
    print("2. Test login and other features")


if __name__ == "__main__":
    main()
