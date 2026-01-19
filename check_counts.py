import psycopg2
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from backend directory
env_path = Path("backend/.env")
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/quantai")
SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").replace("host.docker.internal", "localhost")

def check_counts():
    try:
        conn = psycopg2.connect(SYNC_DATABASE_URL)
        cur = conn.cursor()
        
        # Check stock_candles (legacy)
        cur.execute("SELECT COUNT(*) FROM stock_candles")
        legacy_count = cur.fetchone()[0]
        
        # Check stock_candle (new)
        cur.execute("SELECT COUNT(*) FROM stock_candle")
        new_count = cur.fetchone()[0]
        
        # Check if ETL script is in ingestion_checkpoint
        cur.execute("SELECT COUNT(*) FROM ingestion_checkpoint")
        checkpoint_count = cur.fetchone()[0]

        print(f"Record Count in stock_candles (legacy): {legacy_count}")
        print(f"Record Count in stock_candle (new): {new_count}")
        print(f"Checkpoints in ingestion_checkpoint: {checkpoint_count}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_counts()
