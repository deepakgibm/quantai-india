from database import SessionLocal
from sqlalchemy import text

def inspect_candles():
    session = SessionLocal()
    try:
        print("--- stock_candle Data (3 rows) ---")
        res = session.execute(text("""
            SELECT sc.*, im.symbol 
            FROM stock_candle sc 
            JOIN instrument_master im ON sc.instrument_id = im.instrument_id 
            LIMIT 3
        """))
        for row in res:
            print(dict(zip(res.keys(), row)))
            
        print("\n--- Any Indices in stock_candle? ---")
        res = session.execute(text("""
            SELECT DISTINCT im.symbol 
            FROM stock_candle sc 
            JOIN instrument_master im ON sc.instrument_id = im.instrument_id 
            WHERE im.symbol ILIKE '%NIFTY%' OR im.symbol ILIKE '%BANK%'
        """))
        for row in res:
            print(row[0])
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == '__main__':
    inspect_candles()
