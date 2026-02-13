import psycopg2

DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def list_tables():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    tables = cur.fetchall()
    print("Tables in public schema:")
    for table in tables:
        print(f" - {table[0]}")
    
    conn.close()

if __name__ == "__main__":
    list_tables()
