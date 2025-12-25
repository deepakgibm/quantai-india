import sqlite3

conn = sqlite3.connect('quantai.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [t[0] for t in cursor.fetchall()]
print("=== ALL TABLES ===")
for t in tables:
    print(f"  {t}")

# Check stock_data interval types and counts
print("\n=== STOCK_DATA INTERVALS ===")
cursor.execute("SELECT interval, COUNT(*) as cnt, COUNT(DISTINCT symbol) as symbols FROM stock_data GROUP BY interval ORDER BY cnt DESC")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]:,} records, {row[2]} symbols")

# Check date range for daily interval
print("\n=== DAILY DATA DATE RANGE ===")
for interval in ['1day', 'day', '1d', '1D']:
    cursor.execute(f"SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM stock_data WHERE interval='{interval}'")
    row = cursor.fetchone()
    if row[2] > 0:
        print(f"  {interval}: {row[0]} to {row[1]} ({row[2]:,} records)")

# Get a sample of symbols with most daily data
print("\n=== TOP 10 SYMBOLS BY DAILY RECORD COUNT ===")
cursor.execute("""
    SELECT symbol, COUNT(*) as cnt, MIN(timestamp) as earliest, MAX(timestamp) as latest
    FROM stock_data 
    WHERE interval='1day'
    GROUP BY symbol
    ORDER BY cnt DESC
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} records ({row[2]} to {row[3]})")

# Test a 52-week high calculation for a sample stock
print("\n=== SAMPLE 52-WEEK HIGH TEST (RELIANCE) ===")
cursor.execute("""
    SELECT MAX(high), MIN(low), COUNT(*)
    FROM stock_data 
    WHERE symbol LIKE 'RELIANCE%' AND interval='1day'
    AND timestamp >= datetime('now', '-365 days')
""")
row = cursor.fetchone()
if row[0]:
    print(f"  52-week high: {row[0]}, 52-week low: {row[1]}, records: {row[2]}")

# Get latest close for RELIANCE
cursor.execute("""
    SELECT symbol, close, timestamp
    FROM stock_data 
    WHERE symbol LIKE 'RELIANCE%' AND interval='1day'
    ORDER BY timestamp DESC
    LIMIT 1
""")
row = cursor.fetchone()
if row:
    print(f"  Latest: {row[0]} @ {row[1]} on {row[2]}")

conn.close()
print("\n=== DONE ===")
