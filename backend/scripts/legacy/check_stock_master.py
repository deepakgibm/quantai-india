from sqlalchemy import text
from database import engine

def check_stock_master():
    con = engine.connect()
    try:
        res = con.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'stock_master';"))
        columns = [r[0] for r in res]
        print(f"Columns in stock_master: {columns}")
    finally:
        con.close()

if __name__ == "__main__":
    check_stock_master()
