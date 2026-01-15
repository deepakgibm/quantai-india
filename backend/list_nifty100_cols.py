
import psycopg2
try:
    conn = psycopg2.connect("postgresql://postgres:admin@localhost:5432/quantai")
    cur = conn.cursor()
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'nifty100_daily'")
    cols = cur.fetchall()
    for c in cols:
        print(f"{c[0]}: {c[1]}")
except Exception as e:
    print(f"Error: {e}")
