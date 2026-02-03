import sys
import os
sys.path.append(os.getcwd())

from sqlalchemy import create_engine, text
from config import settings

def check_tables():
    print(f"Checking DB: {settings.SYNC_DATABASE_URL}")
    engine = create_engine(settings.SYNC_DATABASE_URL)
    with engine.connect() as conn:
        print("\n--- Table: stock_candles (New) ---")
        try:
            res = conn.execute(text("SELECT count(*) FROM stock_candles WHERE timeframe='1d'"))
            print(f"Total Rows (1d): {res.scalar()}")
            
            res = conn.execute(text("SELECT symbol, count(*) as c FROM stock_candles WHERE timeframe='1d' GROUP BY symbol ORDER BY c DESC LIMIT 3"))
            print("Sample counts per symbol:")
            for r in res:
                print(f"  {r[0]}: {r[1]}")
        except Exception as e:
            print(f"Error checking stock_candles: {e}")

        print("\n--- Table: stock_data (Legacy) ---")
        try:
            res = conn.execute(text("SELECT count(*) FROM stock_data"))
            print(f"Total Rows: {res.scalar()}")
            
            res = conn.execute(text("SELECT symbol, count(*) as c FROM stock_data GROUP BY symbol ORDER BY c DESC LIMIT 3"))
            print("Sample counts per symbol:")
            for r in res:
                print(f"  {r[0]}: {r[1]}")
        except Exception as e:
            print(f"Error checking stock_data: {e}")

if __name__ == "__main__":
    check_tables()
