import sqlite3
import os

db_path = "quantai.db"
if not os.path.exists(db_path):
    print("DB not found")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, COUNT(*) FROM nifty500_daily WHERE symbol LIKE '%NIFTY%' GROUP BY symbol")
    print(cursor.fetchall())
    conn.close()
