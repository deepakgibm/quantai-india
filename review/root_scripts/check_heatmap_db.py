import os
import sys
from sqlalchemy import create_engine, text

sys.path.append(os.path.join(os.getcwd(), 'backend'))
from config import settings

def check_db():
    print(f"Checking DB: {settings.SYNC_DATABASE_URL}")
    try:
        engine = create_engine(settings.SYNC_DATABASE_URL)
        with engine.connect() as conn:
            # Check for stock_master table
            result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'stock_master')"))
            exists = result.scalar()
            print(f"stock_master exists: {exists}")
            
            if exists:
                # Check row count
                count = conn.execute(text("SELECT COUNT(*) FROM stock_master")).scalar()
                print(f"stock_master rows: {count}")
                # Check columns
                cols = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'stock_master'"))
                print(f"Columns: {[r[0] for r in cols]}")
            else:
                print("creating stock_master table...")
                conn.execute(text("""
                    CREATE TABLE stock_master (
                        symbol TEXT PRIMARY KEY,
                        sector TEXT,
                        instrument_key TEXT,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                """))
                conn.commit()
                print("stock_master created.")
                
                # Check stock_data for symbols to populate?
                # User said stock_master is source of truth.
                # I should probably populate it with dummy sector data if empty for demo.
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
