import sqlite3

conn = sqlite3.connect('quantai.db')
cursor = conn.cursor()

# Check intervals
print("INTERVALS:")
cursor.execute("SELECT interval, COUNT(*) as cnt FROM stock_data GROUP BY interval ORDER BY cnt DESC")
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]}")

# Check daily data count 
print("\nDAILY CHECK:")
cursor.execute("SELECT COUNT(DISTINCT symbol) FROM stock_data WHERE interval='1day'")
print(f"Symbols with 1day: {cursor.fetchone()[0]}")

cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM stock_data WHERE interval='1day'")
row = cursor.fetchone()
print(f"Date range: {row}")

# Sample symbol
print("\nSAMPLE RELIANCE:")
cursor.execute("SELECT MAX(high), MIN(low), COUNT(*) FROM stock_data WHERE symbol='RELIANCE.NS' AND interval='1day'")
row = cursor.fetchone()
print(f"52w high: {row[0]}, low: {row[1]}, count: {row[2]}")

# Check if we have symbols with .NS suffix
print("\nSAMPLE SYMBOLS:")
cursor.execute("SELECT DISTINCT symbol FROM stock_data WHERE interval='1day' LIMIT 15")
for row in cursor.fetchall():
    print(f"  {row[0]}")

conn.close()
