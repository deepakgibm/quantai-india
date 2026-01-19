import psycopg2
import json
from dotenv import load_dotenv
import os
from pathlib import Path

# Load .env
load_dotenv(Path("backend/.env"))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/quantai")
SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").replace("host.docker.internal", "localhost")

def get_schema():
    conn = psycopg2.connect(SYNC_DATABASE_URL)
    cur = conn.cursor()
    
    results = {}
    
    # Get stock_candle schema
    cur.execute("""
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'stock_candle'
        ORDER BY ordinal_position
    """)
    results["stock_candle"] = [{"column": r[0], "type": r[1], "nullable": r[2]} for r in cur.fetchall()]
    
    # Get instrument_master schema
    cur.execute("""
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'instrument_master'
        ORDER BY ordinal_position
    """)
    results["instrument_master"] = [{"column": r[0], "type": r[1], "nullable": r[2]} for r in cur.fetchall()]
    
    # Get stock_candles schema (legacy)
    cur.execute("""
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'stock_candles'
        ORDER BY ordinal_position
    """)
    results["stock_candles_legacy"] = [{"column": r[0], "type": r[1], "nullable": r[2]} for r in cur.fetchall()]
    
    # Get stock_master schema (legacy)
    cur.execute("""
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'stock_master'
        ORDER BY ordinal_position
    """)
    results["stock_master_legacy"] = [{"column": r[0], "type": r[1], "nullable": r[2]} for r in cur.fetchall()]
    
    # Get indexes for stock_candle
    cur.execute("""
        SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'stock_candle'
    """)
    results["stock_candle_indexes"] = [{"name": r[0], "def": r[1]} for r in cur.fetchall()]
    
    # Get indexes for instrument_master
    cur.execute("""
        SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'instrument_master'
    """)
    results["instrument_master_indexes"] = [{"name": r[0], "def": r[1]} for r in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    with open("schema_analysis.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("Schema analysis saved to schema_analysis.json")

if __name__ == "__main__":
    get_schema()
