import psycopg2

conn = psycopg2.connect(
    host='localhost', 
    port=5432, 
    user='postgres', 
    password='admin', 
    database='quantai'
)
cur = conn.cursor()

# Get columns
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'stock_data' ORDER BY ordinal_position")
cols = [r[0] for r in cur.fetchall()]
for col in cols:
    print(f"  - {col}")

conn.close()
