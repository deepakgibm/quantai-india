
import psycopg2
try:
    conn = psycopg2.connect("postgresql://postgres:admin@localhost:5432/quantai")
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.views WHERE table_schema = 'public'")
    views = cur.fetchall()
    print([v[0] for v in views])
except Exception as e:
    print(f"Error: {e}")
