
import psycopg2
try:
    conn = psycopg2.connect("postgresql://postgres:admin@localhost:5432/quantai")
    cur = conn.cursor()
    cur.execute("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'stock_candles'")
    idxs = cur.fetchall()
    for name, ddl in idxs:
        print(f"--- {name} ---")
        print(ddl)
except Exception as e:
    print(f"Error: {e}")
