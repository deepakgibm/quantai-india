import psycopg2
conn=psycopg2.connect('postgresql://postgres:admin@localhost:5432/quantai')
cur=conn.cursor()
cur.execute("SELECT MAX(candle_ts) FROM stock_candle WHERE instrument_id=(SELECT instrument_id FROM instrument_master WHERE symbol='ANGELONE')")
print(cur.fetchone()[0])
conn.close()
