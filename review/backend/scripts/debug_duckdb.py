import duckdb
import os
import sys

# Add current dir to path to import config
sys.path.append(os.getcwd())

try:
    from config import settings
    pg_conn = settings.SYNC_DATABASE_URL
    print(f"PG Connection String: {pg_conn}")
    
    db = duckdb.connect(':memory:')
    db.execute("INSTALL postgres")
    db.execute("LOAD postgres")
    print("Postgres extension loaded successfully")
    
    # Try to scan
    print("Testing postgres_scan...")
    # Clean string if it has postgresql://
    if pg_conn.startswith("postgresql://"):
        cleaned_conn = pg_conn.replace("postgresql://", "host=localhost port=5432 user=postgres password=admin dbname=quantai ")
        # In Docker, localhost might be 'db'
        if os.path.exists('/.dockerenv'):
             cleaned_conn = cleaned_conn.replace("host=localhost", "host=db")
        print(f"Cleaned Conn: {cleaned_conn}")
    else:
        cleaned_conn = pg_conn
        
    db.execute(f"CREATE TABLE test AS SELECT * FROM postgres_scan('{pg_conn}', 'users') LIMIT 1")
    print("Scan successful")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
