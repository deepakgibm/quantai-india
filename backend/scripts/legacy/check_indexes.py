from sqlalchemy import text
from database import engine

def check_indexes():
    con = engine.connect()
    try:
        # Get all indexes for stock_candles
        res = con.execute(text("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'stock_candles';"))
        rows = res.fetchall()
        print(f"Found {len(rows)} indexes:")
        for r in rows:
            print(f"- {r[0]}: {r[1]}")
            
        # Check if 'idx_stock_candles_unique' is UNIQUE
        unique_check = con.execute(text("SELECT count(*) FROM pg_indexes WHERE indexname = 'idx_stock_candles_unique' AND indexdef LIKE 'CREATE UNIQUE INDEX %'"))
        is_unique = unique_check.scalar() > 0
        print(f"Is idx_stock_candles_unique UNIQUE? {'Yes' if is_unique else 'No'}")
        
    finally:
        con.close()

if __name__ == "__main__":
    check_indexes()
