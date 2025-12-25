import sqlite3
conn = sqlite3.connect("quantai.db")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(stock_data)")
print(cursor.fetchall())
conn.close()
