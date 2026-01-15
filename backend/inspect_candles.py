from database import SessionLocal
from sqlalchemy import text

def inspect_candles():
    session = SessionLocal()
    try:
        print("--- stock_candles Data (3 rows) ---")
        res = session.execute(text("SELECT * FROM stock_candles LIMIT 3"))
        for row in res:
            print(dict(zip(res.keys(), row)))
            
        print("\n--- Any Indices in stock_candles? ---")
        res = session.execute(text("SELECT DISTINCT symbol FROM stock_candles WHERE symbol ILIKE '%NIFTY%' OR symbol ILIKE '%BANK%'"))
        for row in res:
            print(row[0])
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == '__main__':
    inspect_candles()
