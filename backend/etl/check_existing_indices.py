
import os
import psycopg2

# Get DB URL from env or default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/quantai")
if "+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

def check_indices():
    print(f"Connecting to {DATABASE_URL}")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("\n--- Existing NIFTY% Symbols ---")
        cur.execute("""
            SELECT instrument_id, symbol, series, exchange, instrument_key 
            FROM instrument_master 
            WHERE symbol LIKE '%NIFTY%' OR symbol LIKE '%VIX%'
            ORDER BY symbol
        """)
        rows = cur.fetchall()
        for r in rows:
            print(r)
            
        print("\n--- Distinct Series ---")
        cur.execute("SELECT DISTINCT series FROM instrument_master")
        print(cur.fetchall())

        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_indices()
