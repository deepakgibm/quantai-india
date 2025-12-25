import sqlite3
import json

conn = sqlite3.connect("quantai.db")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(stock_data)")
schema = cursor.fetchall()
for col in schema:
    print(col)

print("\nSample row:")
cursor.execute("SELECT * FROM stock_data LIMIT 1")
print(cursor.fetchone())
conn.close()
