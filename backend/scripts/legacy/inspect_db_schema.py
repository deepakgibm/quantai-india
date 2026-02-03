from database import SessionLocal
from sqlalchemy import text

def inspect_schema():
    session = SessionLocal()
    try:
        # Inspect stock_master columns
        print("--- stock_master Columns ---")
        res = session.execute(text("SELECT * FROM stock_master LIMIT 0"))
        print(list(res.keys()))
        
        # Inspect stock_candles columns
        print("\n--- stock_candles Columns ---")
        res = session.execute(text("SELECT * FROM stock_candles LIMIT 0"))
        print(list(res.keys()))
        
        # Get sample data from stock_master
        print("\n--- stock_master Data (3 rows) ---")
        res = session.execute(text("SELECT * FROM stock_master LIMIT 3"))
        for row in res:
            # Convert row to dict for clear printing
            print(dict(zip(res.keys(), row)))
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == '__main__':
    inspect_schema()
