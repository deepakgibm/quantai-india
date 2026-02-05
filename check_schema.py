
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
    
    print("Checking columns in stock_candle_history:")
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'stock_candle_history'
    """)
    for row in cur.fetchall():
        print(row[0])
        
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals() and conn: conn.close()
