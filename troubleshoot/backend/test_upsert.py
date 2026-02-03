
import psycopg2
from datetime import datetime, date
try:
    conn = psycopg2.connect("postgresql://postgres:admin@localhost:5432/quantai")
    cur = conn.cursor()
    symbol = "MINDACORP"
    ts = datetime.combine(date(2026, 1, 13), datetime.min.time())
    price = 575.0
    vol = 1000
    
    query = """
        INSERT INTO nifty100_daily (symbol, timestamp, open, high, low, close, volume, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'test_manual')
        ON CONFLICT (symbol, timestamp)
        DO UPDATE SET close = EXCLUDED.close, volume = EXCLUDED.volume
    """
    cur.execute(query, (symbol, ts, price, price, price, price, vol))
    conn.commit()
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
