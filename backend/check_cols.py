from database import SessionLocal
from sqlalchemy import text

def check():
    session = SessionLocal()
    try:
        res = session.execute(text("SELECT * FROM stock_candles LIMIT 1"))
        print("Columns in stock_candles:")
        print(list(res.keys()))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == '__main__':
    check()
