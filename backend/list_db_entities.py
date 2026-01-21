
import psycopg2
import json

try:
    conn = psycopg2.connect("postgresql://postgres:admin@localhost:5432/quantai")
    cur = conn.cursor()
    # List all tables in the public schema
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
    """)
    tables = [t[0] for t in cur.fetchall()]
    
    # List all views just in case
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'VIEW'
    """)
    views = [v[0] for v in cur.fetchall()]
    
    result = {
        "tables": sorted(tables),
        "views": sorted(views)
    }
    
    with open("database_entities.json", "w") as f:
        json.dump(result, f, indent=4)
    
    print(f"Successfully listed {len(tables)} tables and {len(views)} views.")
    print("Tables:", tables)

except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
