
import os
import psycopg2
from datetime import datetime

# Get DB URL from env or default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@quantai-postgres:5432/quantai")
if "+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

INDICES = [
    {
        "symbol": "NIFTY 50",
        "instrument_key": "NSE_INDEX|Nifty 50",
        "exchange": "NSE",
        "series": "INDEX",
        "company_name": "Nifty 50 Index",
        "sector": "INDEX"
    },
    {
        "symbol": "BANK NIFTY",
        "instrument_key": "NSE_INDEX|Nifty Bank",
        "exchange": "NSE",
        "series": "INDEX",
        "company_name": "Nifty Bank Index",
        "sector": "INDEX"
    },
    {
        "symbol": "INDIA VIX",
        "instrument_key": "NSE_INDEX|India VIX",
        "exchange": "NSE",
        "series": "INDEX",
        "company_name": "India VIX Volatility Index",
        "sector": "INDEX"
    }
]

def seed_indices():
    print(f"Connecting to {DATABASE_URL}")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        for idx in INDICES:
            print(f"Processing {idx['symbol']}...")
            
            # 1. Check by instrument_key
            cur.execute("""
                SELECT instrument_id, symbol, series, instrument_key FROM instrument_master 
                WHERE instrument_key = %s
            """, (idx['instrument_key'],))
            row = cur.fetchone()
            
            if row:
                print(f"  -> Found via Key: ID={row[0]}")
                continue

            # 2. Check by (symbol, series, exchange)
            cur.execute("""
                SELECT instrument_id, instrument_key FROM instrument_master 
                WHERE symbol = %s AND series = %s AND exchange = %s
            """, (idx['symbol'], idx['series'], idx['exchange']))
            row = cur.fetchone()
            
            if row:
                print(f"  -> Found via Symbol/Series: ID={row[0]}. Updating Key...")
                # Update the key to match what we expect
                cur.execute("""
                    UPDATE instrument_master
                    SET instrument_key = %s, updated_at = %s
                    WHERE instrument_id = %s
                """, (idx['instrument_key'], datetime.utcnow(), row[0]))
                print(f"     Updated key from {row[1]} to {idx['instrument_key']}")
                continue
                
                # Insert fresh with dummy ISIN
            print(f"  -> Not found. Inserting NEW record (letting DB gen ID)...")
            try:
                cur.execute("""
                    INSERT INTO instrument_master 
                    (symbol, instrument_key, exchange, series, company_name, sector, is_active, isin_code, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, TRUE, 'IN9999999999', %s, %s)
                    RETURNING instrument_id
                """, (
                    idx['symbol'],
                    idx['instrument_key'],
                    idx['exchange'],
                    idx['series'],
                    idx['company_name'],
                    idx['sector'],
                    datetime.utcnow(),
                    datetime.utcnow()
                ))
                new_id = cur.fetchone()[0]
                print(f"  -> Insert Success: ID={new_id}")
            except Exception as e:
                print(f"  -> Insert Error: {e}")
                conn.rollback() 
                print("     Retrying with explicit ID...")
                try:
                    explicit_id = 1000000 + INDICES.index(idx) + 1
                    cur.execute("""
                        INSERT INTO instrument_master 
                        (instrument_id, symbol, instrument_key, exchange, series, company_name, sector, is_active, isin_code, created_at, updated_at)
                        OVERRIDING SYSTEM VALUE
                        VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, 'IN9999999999', %s, %s)
                    """, (
                        explicit_id,
                        idx['symbol'],
                        idx['instrument_key'],
                        idx['exchange'],
                        idx['series'],
                        idx['company_name'],
                        idx['sector'],
                        datetime.utcnow(),
                        datetime.utcnow()
                    ))
                    print(f"  -> Explicit ID Insert Success.")
                except Exception as e2:
                    print(f"     Explicit ID Failed too: {e2}")
                    conn.rollback()

        conn.commit()
        conn.close()
        print("\nSeed completed.")
        
    except Exception as e:
        print(f"Fatal Error: {e}")

if __name__ == "__main__":
    seed_indices()
