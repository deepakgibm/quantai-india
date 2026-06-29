import psycopg2
import os

def list_db_info():
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:admin@127.0.0.1:5432/quantai")
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    db_url = db_url.replace("localhost", "127.0.0.1")
    print(f"Connecting to: {db_url}")
    try:
        conn = psycopg2.connect(db_url, connect_timeout=5)
        cur = conn.cursor()
        
        # Get tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public' 
            ORDER BY table_name;
        """)
        tables = [r[0] for r in cur.fetchall()]
        print(f"Found {len(tables)} tables:")
        
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table};")
            count = cur.fetchone()[0]
            print(f"  - {table}: {count} rows")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    list_db_info()
