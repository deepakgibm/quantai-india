"""Check database data"""
import sqlite3

conn = sqlite3.connect('quantai.db')
cursor = conn.cursor()

# Check max date
cursor.execute("SELECT MAX(date(timestamp)) FROM stock_data")
max_date = cursor.fetchone()[0]
print(f"Latest date in database: {max_date}")

# Check how many symbols have data for the latest date
cursor.execute("""
    SELECT COUNT(DISTINCT symbol) 
    FROM stock_data 
    WHERE date(timestamp) = ?
""", (max_date,))
print(f"Symbols with data on {max_date}: {cursor.fetchone()[0]}")

# Check the previous day
cursor.execute("""
    SELECT MAX(date(timestamp)) 
    FROM stock_data 
    WHERE date(timestamp) < ?
""", (max_date,))
prev_date = cursor.fetchone()[0]
print(f"Previous trading date: {prev_date}")

# Check symbols with both dates
cursor.execute("""
    SELECT COUNT(DISTINCT symbol) 
    FROM stock_data 
    WHERE date(timestamp) >= ?
""", (prev_date,))
print(f"Symbols with data on or after {prev_date}: {cursor.fetchone()[0]}")

conn.close()
