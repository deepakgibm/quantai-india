"""Script to find stocks with missing data for today"""
import psycopg2
from urllib.parse import urlparse
import os

db_url = os.environ.get('DATABASE_URL', '').replace('+asyncpg', '')
result = urlparse(db_url)
conn = psycopg2.connect(
    host=result.hostname or 'host.docker.internal',
    port=result.port or 5432,
    user=result.username or 'postgres',
    password=result.password or 'admin',
    database=result.path.lstrip('/') or 'quantai'
)
cursor = conn.cursor()

# Find stocks in instrument_master with no recent data (no data for today)
cursor.execute('''
    SELECT im.symbol, im.instrument_key
    FROM instrument_master im
    WHERE im.is_active = TRUE
    AND im.exchange = 'NSE'
    AND im.series = 'EQ'
    AND NOT EXISTS (
        SELECT 1 FROM stock_candle sc 
        WHERE sc.instrument_id = im.instrument_id 
        AND sc.candle_ts::date = CURRENT_DATE
    )
    ORDER BY im.symbol
''')

rows = cursor.fetchall()
print("=== Stocks with NO DATA for today ===")
for row in rows:
    print(f"{row[0]}: {row[1]}")

cursor.execute('SELECT COUNT(*) FROM instrument_master WHERE is_active = TRUE AND exchange = %s AND series = %s', ('NSE', 'EQ'))
total = cursor.fetchone()[0]

print(f"\nTotal active stocks: {total}")
print(f"Missing today's data: {len(rows)}")

conn.close()
