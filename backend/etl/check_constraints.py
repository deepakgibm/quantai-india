
import os
import psycopg2

# Get DB URL from env or default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@quantai-postgres:5432/quantai")
if "+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

def check_constraints():
    print(f"Connecting to {DATABASE_URL}")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("\n--- Columns ---")
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'instrument_master'
        """)
        for row in cur.fetchall():
            print(row)
            
        print("\n--- Constraints ---")
        cur.execute("""
            SELECT conname, contype, pg_get_constraintdef(oid) 
            FROM pg_constraint 
            WHERE conrelid = 'instrument_master'::regclass
        """)
        for row in cur.fetchall():
            print(row)
            
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_constraints()
