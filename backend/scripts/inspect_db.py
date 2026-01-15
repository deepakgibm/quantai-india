import psycopg2
import os

def inspect_db():
    try:
        conn = psycopg2.connect(
            host='host.docker.internal', 
            database='quantai', 
            user='postgres', 
            password='admin'
        )
        cur = conn.cursor()
        
        # Get all tables
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = cur.fetchall()
        print(f"Total tables: {len(tables)}")
        
        for table in [t[0] for t in tables]:
            print(f"\n--- Table: {table} ---")
            cur.execute(f"SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = '{table}'")
            columns = cur.fetchall()
            for col in columns:
                print(f"  {col[0]:<25} | {col[1]:<20} | Nullable: {col[2]}")
                
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_db()
