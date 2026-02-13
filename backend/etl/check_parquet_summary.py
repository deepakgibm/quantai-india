import psycopg2

DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def get_summary():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT status, count(*) 
        FROM parquet_load_audit 
        GROUP BY status
    """)
    rows = cur.fetchall()
    
    print("--- PARQUET MIGRATION SUMMARY ---")
    total = 0
    for status, count in rows:
        print(f"{status}: {count}")
        total += count
    print(f"Total Batches: {total}")
    
    cur.execute("SELECT count(distinct symbol) FROM parquet_load_audit WHERE status = 'SUCCESS'")
    symbols = cur.fetchone()[0]
    print(f"Successfully Migrated Symbols: {symbols}")
    
    conn.close()

if __name__ == "__main__":
    get_summary()
