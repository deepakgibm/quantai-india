
import psycopg2
try:
    conn = psycopg2.connect("postgresql://postgres:admin@localhost:5432/quantai")
    cur = conn.cursor()
    cur.execute("SELECT pg_get_indexdef(indexrelid) FROM pg_index WHERE indrelid = 'nifty100_daily'::regclass")
    idxs = cur.fetchall()
    for i in idxs:
        print(i[0])
except Exception as e:
    print(f"Error: {e}")
