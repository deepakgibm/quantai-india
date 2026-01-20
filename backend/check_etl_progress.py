
import os
import psycopg2
from datetime import datetime

try:
    conn = psycopg2.connect(os.getenv("SYNC_DATABASE_URL"))
    cur = conn.cursor()
    
    # Check total rows
    cur.execute("SELECT count(*) FROM stock_candle")
    total_rows = cur.fetchone()[0]
    print(f"Total stock_candle rows: {total_rows}")
    
    # Check checkpoints
    cur.execute("""
        SELECT instrument_key, timeframe, last_date, updated_at 
        FROM ingestion_checkpoint 
        ORDER BY updated_at DESC
        LIMIT 5
    """)
    print("\nRecent Checkpoints:")
    for row in cur.fetchall():
        print(f"  Key: {row[0]} | TF: {row[1]} | Date: {row[2]} | Updated: {row[3]}")
        
    # Check active connection queries (optional, if user has pg_stat_activity access)
    # cur.execute("SELECT pid, query_start, state, query FROM pg_stat_activity WHERE query LIKE '%INSERT INTO stock_candle%'")
    # print("\nActive Inserts:")
    # for row in cur.fetchall():
    #     print(f"  {row}")

except Exception as e:
    print(f"Error: {e}")
