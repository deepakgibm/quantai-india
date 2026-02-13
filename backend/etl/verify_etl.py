import psycopg2
from datetime import datetime

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': 'admin',
    'database': 'quantai'
}

def check_counts():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("SELECT count(*) FROM stock_candle_history")
    total_candles = cur.fetchone()[0]
    print(f"Total Candles in history: {total_candles}")
    
    cur.execute("SELECT symbol, status, last_updated FROM etl_job_status WHERE job_name = 'backfill_2022' LIMIT 10")
    rows = cur.fetchall()
    print("\nJob Status (First 10):")
    for row in rows:
        print(f" {row[0]}: {row[1]} (Last Updated: {row[2]})")
        
    cur.execute("""
        SELECT symbol, timeframe, count(*), MAX(candle_ts) 
        FROM stock_candle_history h
        JOIN instrument_master i ON h.instrument_id = i.instrument_id
        GROUP BY symbol, timeframe
        LIMIT 10
    """)
    rows = cur.fetchall()
    print("\nSample counts per symbol/timeframe:")
    for row in rows:
        print(f" {row[0]} ({row[1]}m): {row[2]} records, Max TS: {row[3]}")
        
    conn.close()

if __name__ == "__main__":
    check_counts()
