
import os
import psycopg2
from urllib.parse import urlparse

# Get DB URL from env or default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@quantai-postgres:5432/quantai")
# Convert asyncpg to psycopg2 if needed
if "+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

def check_schema():
    print(f"Connecting to {DATABASE_URL}")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("\nChecking for NIFTY/INDIA VIX/BANK NIFTY symbols:")
        cur.execute("""
            SELECT instrument_id, symbol, exchange, segment, series, instrument_key 
            FROM instrument_master 
            WHERE symbol IN ('NIFTY 50', 'BANK NIFTY', 'INDIA VIX', 'Nifty 50', 'Nifty Bank')
        """)
        rows = cur.fetchall()
        
        if not rows:
            print("No index rows found!")
        else:
            print(f"Found {len(rows)} rows:")
            for row in rows:
                print(row)
                
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schema()
