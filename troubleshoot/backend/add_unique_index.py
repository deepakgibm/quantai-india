from sqlalchemy import text
from database import engine

def add_index():
    con = engine.connect()
    print("Adding unique constraint to stock_candles table...")
    try:
        con.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_stock_candles_unique 
            ON stock_candles (symbol, timestamp, timeframe);
        """))
        print("Successfully added/verified unique index.")
    except Exception as e:
        print(f"Error adding index: {e}")
    finally:
        con.close()

if __name__ == "__main__":
    add_index()
