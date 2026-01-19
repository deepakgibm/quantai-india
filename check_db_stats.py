import psycopg2
import os
import json
from dotenv import load_dotenv
from pathlib import Path

# Load .env from backend directory
env_path = Path("backend/.env")
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/quantai")
SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").replace("host.docker.internal", "localhost")

def check_counts():
    results = {}
    try:
        conn = psycopg2.connect(SYNC_DATABASE_URL)
        cur = conn.cursor()
        
        # Check stock_candles (legacy)
        cur.execute("SELECT COUNT(*) FROM stock_candles")
        results["stock_candles_legacy"] = cur.fetchone()[0]
        
        # Check stock_candle (new)
        cur.execute("SELECT COUNT(*) FROM stock_candle")
        results["stock_candle_new"] = cur.fetchone()[0]
        
        # Check if ETL script is in ingestion_checkpoint
        cur.execute("SELECT COUNT(*) FROM ingestion_checkpoint")
        results["ingestion_checkpoint"] = cur.fetchone()[0]
        
        # Check last timestamp in stock_candle
        cur.execute("SELECT MAX(candle_ts) FROM stock_candle")
        results["last_candle_ts"] = str(cur.fetchone()[0])

        cur.close()
        conn.close()
    except Exception as e:
        results["error"] = str(e)
    
    with open("db_stats.json", "w") as f:
        json.dump(results, f, indent=4)

if __name__ == "__main__":
    check_counts()
