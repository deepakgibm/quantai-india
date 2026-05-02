import psycopg2
conn=psycopg2.connect('postgresql://postgres:admin@localhost:5432/quantai')
cur=conn.cursor()
cur.execute("SELECT COUNT(1) FROM stock_candle")
print(f"Total rows in stock_candle: {cur.fetchone()[0]}")
conn.close()
