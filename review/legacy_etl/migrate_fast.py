"""
Super-Fast Partial Migration Script
Migrates only the most recent 100 candles for the first 50 symbols.
"""

import sqlite3
import psycopg2
from datetime import datetime

SQLITE_PATH = r'C:\Users\Deepak Kumar\Downloads\test\stock_data_v1.db'
PG_CONN_STR = "host=localhost dbname=quantai user=postgres password=admin"

def run_super_fast_migration():
    print("=" * 60)
    print("Super-Fast Migration (50 symbols only)")
    print("=" * 60)
    
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()
    
    pg_conn = psycopg2.connect(PG_CONN_STR)
    pg_cur = pg_conn.cursor()
    
    table_name = sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite%'").fetchone()[0]
    
    print("Fetching top 50 symbols...")
    symbols = sqlite_cur.execute(f"SELECT DISTINCT symbol FROM {table_name} LIMIT 50").fetchall()
    
    print(f"\n[STEP 1] Truncating PostgreSQL stock_data table...")
    pg_cur.execute("TRUNCATE TABLE stock_data RESTART IDENTITY CASCADE")
    pg_conn.commit()
    
    print("\n[STEP 2] Migrating 100 candles per symbol...")
    total = 0
    for symbol_row in symbols:
        symbol = symbol_row[0]
        sqlite_cur.execute(f"SELECT * FROM {table_name} WHERE symbol = ? ORDER BY timestamp DESC LIMIT 100", (symbol,))
        rows = sqlite_cur.fetchall()
        
        for row in rows:
            row_dict = dict(row)
            ts_str = str(row_dict.get('timestamp'))
            try:
                timestamp = datetime.fromisoformat(ts_str.replace('Z', '+00:00').replace('+00:00', ''))
            except:
                timestamp = datetime.now()
                
            pg_cur.execute('''
                INSERT INTO stock_data (symbol, timestamp, "open", high, low, "close", volume, "interval", source, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            ''', (symbol, timestamp, row_dict.get('open'), row_dict.get('high'), row_dict.get('low'), row_dict.get('close'), 
                  int(float(row_dict.get('volume', 0))),'1day', 'upstox', datetime.utcnow()))
        
        total += len(rows)
        print(f"  Migrated {symbol} ({len(rows)} rows)")
    
    pg_conn.commit()
    sqlite_conn.close()
    pg_conn.close()
    print(f"\nDone! Migrated {total} rows.")

if __name__ == "__main__":
    run_super_fast_migration()
