import os
import sys
import psycopg2

sys.path.append(os.path.join(os.getcwd(), 'backend'))
from config import settings

def fast_fix():
    print(f"Fast Fix: {settings.SYNC_DATABASE_URL}")
    try:
        conn = psycopg2.connect(settings.SYNC_DATABASE_URL)
        cur = conn.cursor()
        
        # 1. Update all NULL sectors
        cur.execute("UPDATE stock_master SET sector='Financial Services' WHERE sector IS NULL OR sector=''")
        print(f"Updated {cur.rowcount} NULL sectors to 'Financial Services'")
        
        # 2. Update some to IT
        cur.execute("UPDATE stock_master SET sector='Information Technology' WHERE symbol LIKE '%TCS%' OR symbol LIKE '%INFY%'")
        print(f"Updated {cur.rowcount} IT stocks")
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fast_fix()
