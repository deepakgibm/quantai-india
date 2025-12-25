import sqlite3

conn = sqlite3.connect('quantai.db')
cursor = conn.cursor()

# Check stock_data table
cursor.execute("SELECT COUNT(*) FROM stock_data")
count = cursor.fetchone()[0]
print(f"stock_data row count: {count}")

cursor.execute("PRAGMA table_info(stock_data)")
cols = [c[1] for c in cursor.fetchall()]
print(f"Columns: {cols}")

cursor.execute("SELECT DISTINCT symbol FROM stock_data LIMIT 20")
symbols = cursor.fetchall()
print(f"Sample symbols ({len(symbols)}): {symbols}")

if count > 0:
    cursor.execute("SELECT * FROM stock_data LIMIT 5")
    rows = cursor.fetchall()
    print("Sample rows:")
    for row in rows:
        print(f"  {row}")

conn.close()
