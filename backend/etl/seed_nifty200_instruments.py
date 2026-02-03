
import os
import json
import psycopg2
from datetime import datetime
from pathlib import Path

# Get DB URL from env or default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@host.docker.internal:5432/quantai")
if "+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

def seed_nifty200():
    print(f"Connecting to {DATABASE_URL}")
    
    # Path to nifty200_instruments.json
    json_path = Path(__file__).parent.parent / "nifty200_instruments.json"
    if not json_path.exists():
        print(f"Error: {json_path} not found")
        return

    with open(json_path, 'r') as f:
        instruments = json.load(f)
    
    print(f"Loaded {len(instruments)} instruments from JSON")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        count = 0
        for symbol, instrument_key in instruments:
            # 1. Check if exists
            cur.execute("SELECT instrument_id FROM instrument_master WHERE instrument_key = %s", (instrument_key,))
            if cur.fetchone():
                continue
            
            # 2. Insert
            try:
                cur.execute("""
                    INSERT INTO instrument_master 
                    (symbol, instrument_key, exchange, series, company_name, sector, is_active, isin_code, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s, %s, %s)
                """, (
                    symbol,
                    instrument_key,
                    "NSE",
                    "EQ",
                    symbol,
                    "Unknown",
                    f"IN_{symbol}_DUMMY",
                    datetime.utcnow(),
                    datetime.utcnow()
                ))
                count += 1
            except Exception as e:
                print(f"Error inserting {symbol}: {e}")
                conn.rollback()
                continue
        
        conn.commit()
        conn.close()
        print(f"Seed completed. Inserted {count} new instruments.")
        
    except Exception as e:
        print(f"Fatal Error: {e}")

if __name__ == "__main__":
    seed_nifty200()
