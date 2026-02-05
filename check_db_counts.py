
import psycopg2
import os

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': 'admin',
    'database': 'quantai'
}

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    print("Checking stock_candle_history count...")
    cur.execute("SELECT COUNT(*) FROM stock_candle_history")
    count = cur.fetchone()[0]
    print(f"stock_candle_history rows: {count}")
    
    print("\nChecking for any recent history data (limit 5):")
    cur.execute("SELECT * FROM stock_candle_history ORDER BY candle_ts DESC LIMIT 5")
    for row in cur.fetchall():
        print(row)
        
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals() and conn: conn.close()
