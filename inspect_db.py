
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

try:
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    print("Checking sample rows from instrument_master:")
    cur.execute("SELECT symbol, series, exchange FROM instrument_master LIMIT 10")
    for row in cur.fetchall():
        print(row)
        
    print("\nChecking ZOMATO specifically:")
    cur.execute("SELECT * FROM instrument_master WHERE symbol LIKE '%ZOMATO%'")
    rows = cur.fetchall()
    if rows:
        for row in rows:
            print(row)
    else:
        print("ZOMATO not found in any form.")
        
except Exception as e:
    print(e)
finally:
    if conn: conn.close()
