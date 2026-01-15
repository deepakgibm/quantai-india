"""Check what symbols are actually in the database"""
import sqlite3

db_path = r"c:\Users\Deepak Kumar\Downloads\quantai-india\quantai_review_later\quantai.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# First check what tables exist
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]
print(f"Tables: {tables}")

# Check symbols in stock_data
if 'stock_data' in tables:
    cursor.execute("SELECT DISTINCT symbol FROM stock_data")
    symbols = [r[0] for r in cursor.fetchall()]
    print(f"\nstock_data symbols ({len(symbols)}): {symbols[:20]}...")
    
    # Check intervals
    cursor.execute("SELECT DISTINCT interval FROM stock_data")
    intervals = [r[0] for r in cursor.fetchall()]
    print(f"Intervals: {intervals}")
else:
    print("No stock_data table!")

# Check nifty_100_daily
if 'nifty_100_daily' in tables:
    cursor.execute("SELECT DISTINCT symbol FROM nifty_100_daily")
    symbols = [r[0] for r in cursor.fetchall()]
    print(f"\nnifty_100_daily symbols ({len(symbols)}): {symbols[:20]}...")
else:
    print("No nifty_100_daily table!")

conn.close()
