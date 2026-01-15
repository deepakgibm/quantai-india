from sqlalchemy import text
from database import engine
import json

def check_stocks():
    con = engine.connect()
    try:
        query = text("SELECT * FROM stock_master WHERE symbol IN ('360ONE', 'ADANIENSOL')")
        res = con.execute(query)
        keys = res.keys()
        for row in res:
            print(dict(zip(keys, row)))
    finally:
        con.close()

if __name__ == "__main__":
    check_stocks()
