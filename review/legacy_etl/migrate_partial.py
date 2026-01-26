"""
SQLite to PostgreSQL Partial Migration Script
Migrates only the most recent 200 candles per symbol/interval for fast scanner startup.
"""

import sqlite3
import psycopg2
from datetime import datetime

SQLITE_PATH = r'C:\Users\Deepak Kumar\Downloads\test\stock_data_v1.db'
PG_CONN_STR = "host=localhost dbname=quantai user=postgres password=admin"

def run_partial_migration():
    print("=" * 60)
    print("SQLite to PostgreSQL Partial Migration (Recent Data Only)")
    print("=" * 60)
    
    # Connect
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()
    
    pg_conn = psycopg2.connect(PG_CONN_STR)
    pg_cur = pg_conn.cursor()
    
    # Get table name
    table_name = sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite%'").fetchone()[0]
    print(f"Source Table: {table_name}")
    
    # Get distinct symbols and intervals
    print("Fetching distinct symbols and intervals...")
    combos = sqlite_cur.execute(f"SELECT DISTINCT symbol, timeframe FROM {table_name}").fetchall()
    print(f"Found {len(combos)} symbol/interval combinations.")
    
    # Truncate PG table
    print("\n[STEP 1] Truncating PostgreSQL stock_data table...")
    pg_cur.execute("TRUNCATE TABLE stock_data RESTART IDENTITY CASCADE")
    pg_conn.commit()
    
    # Migrate most recent 200 for each
    print("\n[STEP 2] Migrating most recent 200 candles for each combination...")
    
    migrated_total = 0
    for i, combo in enumerate(combos):
        symbol = combo['symbol']
        interval = combo['timeframe']
        
        # Fetch latest 200
        sqlite_cur.execute(f"""
            SELECT * FROM {table_name} 
            WHERE symbol = ? AND timeframe = ? 
            ORDER BY timestamp DESC 
            LIMIT 300
        """, (symbol, interval))
        
        rows = sqlite_cur.fetchall()
        if not rows:
            continue
            
        # Insert into PG
        batch_data = []
        for row in rows:
            row_dict = dict(row)
            
            # Parse timestamp (same logic as before)
            ts_str = str(row_dict.get('timestamp'))
            try:
                if 'T' in ts_str:
                    timestamp = datetime.fromisoformat(ts_str.replace('Z', '+00:00').replace('+00:00', ''))
                else:
                    timestamp = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
            except:
                timestamp = datetime.now()
                
            batch_data.append((
                symbol, timestamp, row_dict.get('open'), row_dict.get('high'), 
                row_dict.get('low'), row_dict.get('close'), 
                int(float(row_dict.get('volume', 0))), 
                row_dict.get('timeframe', '1day'), 'upstox', datetime.utcnow()
            ))
            
        # Bulk insert
        args_str = ','.join(pg_cur.mogrify("(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", x).decode('utf-8') for x in batch_data)
        pg_cur.execute(f"INSERT INTO stock_data (symbol, timestamp, \"open\", high, low, \"close\", volume, \"interval\", source, created_at) VALUES " + args_str + " ON CONFLICT DO NOTHING")
        
        migrated_total += len(rows)
        if (i + 1) % 100 == 0:
            pg_conn.commit()
            print(f"  Processed {i+1}/{len(combos)} combinations... ({migrated_total} rows)")
            
    pg_conn.commit()
    print(f"\nFinal row count: {migrated_total}")
    
    sqlite_conn.close()
    pg_conn.close()
    print("\nPartial Migration Complete!")

if __name__ == "__main__":
    run_partial_migration()
