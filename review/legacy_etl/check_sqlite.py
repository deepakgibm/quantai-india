"""Check available timeframes in SQLite database"""
import sqlite3
import os

# Find the database file
db_paths = [
    r"c:\Users\Deepak Kumar\Downloads\quantai-india\quantai_review_later\quantai.db",
    r"c:\Users\Deepak Kumar\Downloads\quantai-india\backend\quantai.db",
    r"c:\Users\Deepak Kumar\Downloads\quantai-india\quantai.db",
]

db_path = None
for path in db_paths:
    if os.path.exists(path):
        db_path = path
        break

if not db_path:
    print("No database file found!")
    exit()

print(f"Using database: {db_path}")
print(f"Size: {os.path.getsize(db_path) / 1024 / 1024:.2f} MB")
print()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]
print(f"Tables: {tables}")
print()

# Check nifty_100_daily
if 'nifty_100_daily' in tables:
    cursor.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM nifty_100_daily")
    row = cursor.fetchone()
    print(f"nifty_100_daily: {row[0]} rows, {row[1]} to {row[2]}")
    
    cursor.execute("SELECT DISTINCT symbol FROM nifty_100_daily LIMIT 10")
    symbols = [r[0] for r in cursor.fetchall()]
    print(f"  Symbols: {symbols}")

# Check stock_data
if 'stock_data' in tables:
    cursor.execute("SELECT interval, COUNT(*) FROM stock_data GROUP BY interval")
    for row in cursor.fetchall():
        print(f"stock_data({row[0]}): {row[1]} rows")

# Check RELIANCE
print()
print("RELIANCE availability:")
if 'nifty_100_daily' in tables:
    cursor.execute("SELECT COUNT(*) FROM nifty_100_daily WHERE symbol = 'RELIANCE'")
    print(f"  Daily: {cursor.fetchone()[0]} rows")

if 'stock_data' in tables:
    cursor.execute("SELECT interval, COUNT(*) FROM stock_data WHERE symbol = 'RELIANCE' GROUP BY interval")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} rows")

conn.close()
