"""Debug warm-up"""
import psycopg2
from config import settings

print(f"Connecting to: {settings.SYNC_DATABASE_URL}")

conn = psycopg2.connect(settings.SYNC_DATABASE_URL)
cur = conn.cursor()

# Check what symbols exist
cur.execute("SELECT DISTINCT symbol FROM stock_data LIMIT 10")
symbols_in_db = [row[0] for row in cur.fetchall()]
print(f"Sample symbols in DB: {symbols_in_db}")

# Check if RELIANCE exists
cur.execute("SELECT symbol, COUNT(*) FROM stock_data WHERE symbol = 'RELIANCE' GROUP BY symbol")
result = cur.fetchone()
print(f"RELIANCE rows: {result}")

# Try a specific query
cur.execute("""
    SELECT timestamp, "open", high, low, "close", volume
    FROM stock_data
    WHERE symbol = %s AND "interval" = %s
    ORDER BY timestamp DESC
    LIMIT 5
""", ('RELIANCE', '1d'))
rows = cur.fetchall()
print(f"RELIANCE 1d candles: {len(rows)}")
if rows:
    print(f"Sample row: {rows[0]}")

conn.close()
