from sqlalchemy import text
from database import engine
import json

def dump_stock_master():
    con = engine.connect()
    try:
        query = text("SELECT symbol, instrument_key FROM stock_master")
        res = con.execute(query)
        data = {r[0]: r[1] for r in res}
        with open("stock_master_dump.json", "w") as f:
            json.dump(data, f, indent=2)
        print(f"Dumped {len(data)} stocks to stock_master_dump.json")
    finally:
        con.close()

if __name__ == "__main__":
    dump_stock_master()
