import os
import sys
from sqlalchemy import create_engine, text

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from config import settings

def check_db():
    print(f"Checking DB: {settings.SYNC_DATABASE_URL}")
    try:
        engine = create_engine(settings.SYNC_DATABASE_URL)
        with engine.connect() as conn:
            # Check stock_data
            result = conn.execute(text("SELECT COUNT(*), COUNT(DISTINCT symbol) FROM stock_data"))
            row = result.fetchone()
            print(f"Stock Data: {row[0]} rows, {row[1]} symbols")
            
            if row[0] == 0:
                print("❌ stock_data table is EMPTY!")
            
            # Check Nifty100Daily
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM nifty100_daily"))
                print(f"Nifty100Daily: {result.scalar()} rows")
            except Exception as e:
                print(f"Nifty100Daily check failed: {e}")

    except Exception as e:
        print(f"❌ DB Connection failed: {e}")

if __name__ == "__main__":
    check_db()
