import psycopg2

def check_dependencies():
    DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        print("Checking partitions for stock_candle...")
        cur.execute("""
            SELECT inhrelid::regclass AS child 
            FROM pg_inherits 
            WHERE inhparent = 'stock_candle'::regclass
        """)
        partitions = cur.fetchall()
        print(f"Partitions found: {len(partitions)}")
        for p in partitions:
            print(f"  - {p[0]}")
            
        print("\nChecking foreign key dependencies on stock_candle...")
        cur.execute("""
            SELECT conname, relname 
            FROM pg_constraint c 
            JOIN pg_class r ON c.conrelid = r.oid 
            WHERE confrelid = 'stock_candle'::regclass
        """)
        dependencies = cur.fetchall()
        print(f"Dependencies found: {len(dependencies)}")
        for d in dependencies:
            print(f"  - Constraint {d[0]} on table {d[1]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_dependencies()
