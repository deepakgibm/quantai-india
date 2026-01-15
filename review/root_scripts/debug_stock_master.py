import os
import sys
from sqlalchemy import create_engine, text

sys.path.append(os.path.join(os.getcwd(), 'backend'))
from config import settings

def inspect_stock_master():
    print(f"Checking stock_master content: {settings.SYNC_DATABASE_URL}")
    try:
        engine = create_engine(settings.SYNC_DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT symbol, sector FROM stock_master LIMIT 10"))
            rows = result.fetchall()
            print(f"Sample Rows: {rows}")
            
            # Check null sectors
            null_count = conn.execute(text("SELECT COUNT(*) FROM stock_master WHERE sector IS NULL OR sector = ''")).scalar()
            print(f"Rows with NULL/Empty Sector: {null_count}")

            # Check overlap with stock_data
            overlap = conn.execute(text("SELECT COUNT(*) FROM stock_master sm JOIN stock_data sd ON sm.symbol = sd.symbol")).scalar()
            print(f"Overlap with stock_data: {overlap} (approx rows)")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_stock_master()
