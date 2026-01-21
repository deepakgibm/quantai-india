
import os
import psycopg2
from datetime import datetime

# Get DB URL from env or default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@quantai-postgres:5432/quantai")
if "+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

def check_status():
    print(f"Connecting to {DATABASE_URL}...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # 1. Check Row Counts
        print("\n--- Row Counts ---")
        try:
            cur.execute("SELECT count(*) FROM stock_candle")
            print(f"stock_candle (Active Table): {cur.fetchone()[0]}")
        except Exception as e:
            print(f"stock_candle: Error ({e})")
            conn.rollback()
            
        try:
            cur.execute("SELECT count(*) FROM stock_candles")
            print(f"stock_candles (Legacy Table): {cur.fetchone()[0]}")
        except Exception:
            conn.rollback()

        # 2. Check Recent Checkpoints
        print("\n--- Latest 10 Updates (ingestion_checkpoint) ---")
        cur.execute("""
            SELECT instrument_key, timeframe, last_date, updated_at 
            FROM ingestion_checkpoint 
            ORDER BY updated_at DESC 
            LIMIT 10
        """)
        rows = cur.fetchall()
        if not rows:
            print("No checkpoints found.")
        else:
            print(f"{'Instrument':<30} | {'TF':<5} | {'Last Data':<12} | {'Updated At':<20}")
            print("-" * 80)
            for r in rows:
                inst = r[0].split('|')[-1][:28] # truncated simple name
                tf = r[1]
                ldata = str(r[2])
                if isinstance(r[3], str):
                   updated = r[3]
                else:
                   updated = r[3].strftime("%H:%M:%S") if r[3] else "N/A"
                print(f"{inst:<30} | {tf:<5} | {ldata:<12} | {updated:<20}")

        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_status()
