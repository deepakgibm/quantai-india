from database import SessionLocal
from sqlalchemy import text

def list_symbols():
    session = SessionLocal()
    try:
        res = session.execute(text("SELECT DISTINCT symbol FROM stock_candles"))
        symbols = [row[0] for row in res]
        print(f"Total symbols: {len(symbols)}")
        print(f"Sample: {symbols[:50]}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == '__main__':
    list_symbols()
