
import psycopg2
try:
    conn = psycopg2.connect("postgresql://postgres:admin@localhost:5432/quantai")
    cur = conn.cursor()
    cur.execute("SELECT conname FROM pg_constraint WHERE conrelid = 'nifty100_daily'::regclass")
    cons = cur.fetchall()
    for c in cons:
        print(c[0])
except Exception as e:
    print(f"Error: {e}")
