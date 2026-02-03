from sqlalchemy import text
from database import engine

def check_columns():
    con = engine.connect()
    try:
        res = con.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'stock_candles';"))
        rows = res.fetchall()
        print(f"Columns in stock_candles:")
        for r in rows:
            print(f"- {r[0]}")
    finally:
        con.close()

if __name__ == "__main__":
    check_columns()
