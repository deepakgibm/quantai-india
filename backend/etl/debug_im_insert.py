
import os
import psycopg2
import traceback

# Get DB URL from env or default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/quantai")
if "+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

def debug_insert():
    print(f"Connecting to {DATABASE_URL}")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("Checking existing NIFTY 50...")
        cur.execute("SELECT * FROM instrument_master WHERE symbol ILIKE '%NIFTY 50%'")
        rows = cur.fetchall()
        for r in rows:
            print(f"EXISTING: {r}")

        print("\nAttempting Insert...")
        try:
            cur.execute("""
                INSERT INTO instrument_master 
                (instrument_id, symbol, instrument_key, exchange, series, company_name, sector, is_active, created_at, updated_at)
                VALUES (999999, 'TEST_SYM_2', 'TEST|KEY_2', 'NSE', 'EQ', 'Test Company 2', 'TEST', TRUE, NOW(), NOW())
                RETURNING instrument_id
            """)
            print(f"Success: {cur.fetchone()}")
            conn.rollback() # Don't commit, just testing
        except Exception as e:
            print("\n!!! INSERT ERROR !!!")
            print(e)
            print(e.pgerror)
            print("!!! END ERROR !!!")
            
        conn.close()
        
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    debug_insert()
