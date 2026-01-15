"""
SQLite to PostgreSQL Migration Script (Sync Version)
Uses psycopg2 for direct PostgreSQL access and sqlite3 for source.
"""

import sqlite3
import psycopg2
from datetime import datetime

SQLITE_PATH = r'C:\Users\Deepak Kumar\Downloads\test\stock_data_v1.db'
PG_CONN_STR = "host=localhost dbname=quantai user=postgres password=admin"
BATCH_SIZE = 5000

def run_migration():
    print("=" * 60)
    print("SQLite to PostgreSQL Migration (Sync)")
    print("=" * 60)
    
    # Connect to SQLite
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    cur = sqlite_conn.cursor()
    
    # Get SQLite table info
    tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite%'").fetchall()
    table_name = tables[0][0]
    print(f"Source Table: {table_name}")
    
    # Get columns
    cols = cur.execute(f"PRAGMA table_info({table_name})").fetchall()
    print(f"SQLite Columns: {[c[1] for c in cols]}")
    
    total_rows = cur.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    print(f"Total Rows to Migrate: {total_rows}")
    
    # Connect to PostgreSQL
    pg_conn = psycopg2.connect(PG_CONN_STR)
    pg_cur = pg_conn.cursor()
    
    # TRUNCATE PostgreSQL table
    print("\n[STEP 1] Truncating PostgreSQL stock_data table...")
    pg_cur.execute("TRUNCATE TABLE stock_data RESTART IDENTITY CASCADE")
    pg_conn.commit()
    print("Truncation complete.")
    
    # Migrate data in batches
    print(f"\n[STEP 2] Migrating {total_rows} rows in batches of {BATCH_SIZE}...")
    
    offset = 0
    migrated = 0
    
    while offset < total_rows:
        rows = cur.execute(f"SELECT * FROM {table_name} LIMIT {BATCH_SIZE} OFFSET {offset}").fetchall()
        
        if not rows:
            break
        
        # Prepare batch insert
        for row in rows:
            row_dict = dict(row)
            
            symbol = row_dict.get('symbol')
            timestamp_str = row_dict.get('timestamp')
            open_price = row_dict.get('open')
            high = row_dict.get('high')
            low = row_dict.get('low')
            close = row_dict.get('close')
            volume = int(float(row_dict.get('volume', 0)))
            interval = row_dict.get('timeframe', row_dict.get('interval', '1day'))
            source = 'upstox'
            
            # Parse timestamp
            try:
                if 'T' in str(timestamp_str):
                    timestamp = datetime.fromisoformat(str(timestamp_str).replace('Z', '+00:00').replace('+00:00', ''))
                else:
                    timestamp = datetime.strptime(str(timestamp_str), '%Y-%m-%d %H:%M:%S')
            except Exception as e:
                print(f"Timestamp parse error for {timestamp_str}: {e}")
                timestamp = datetime.now()
            
            # Insert
            pg_cur.execute('''
                INSERT INTO stock_data (symbol, timestamp, "open", high, low, "close", volume, "interval", source, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, timestamp, "interval") DO NOTHING
            ''', (symbol, timestamp, open_price, high, low, close, volume, interval, source, datetime.utcnow()))
        
        pg_conn.commit()
        migrated += len(rows)
        offset += BATCH_SIZE
        print(f"  Migrated {migrated}/{total_rows} rows ({100*migrated/total_rows:.1f}%)")
    
    # Verify
    print("\n[STEP 3] Verifying migration...")
    pg_cur.execute("SELECT COUNT(*) FROM stock_data")
    pg_count = pg_cur.fetchone()[0]
    print(f"PostgreSQL row count: {pg_count}")
    
    sqlite_conn.close()
    pg_conn.close()
    
    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)

if __name__ == "__main__":
    run_migration()
