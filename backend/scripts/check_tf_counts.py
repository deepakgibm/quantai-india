import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

def check_data_counts():
    env_path = Path("backend/.env")
    load_dotenv(env_path)
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not found")
        return
        
    sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace("host.docker.internal", "localhost")
    
    try:
        conn = psycopg2.connect(sync_url)
        cur = conn.cursor()
        
        print("Timeframe distribution in stock_candle:")
        cur.execute("SELECT timeframe, count(*) FROM stock_candle GROUP BY timeframe ORDER BY timeframe")
        rows = cur.fetchall()
        for tf, count in rows:
            print(f"Timeframe {tf}m: {count} rows")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_data_counts()
