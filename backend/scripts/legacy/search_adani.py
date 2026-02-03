from sqlalchemy import text
from database import engine

def search_adani():
    con = engine.connect()
    try:
        query = text("SELECT symbol, company_name, instrument_key FROM stock_master WHERE company_name ILIKE '%Adani%' OR symbol ILIKE '%Adani%'")
        res = con.execute(query)
        for row in res:
            print(f"Symbol: {row[0]}, Name: {row[1]}, Key: {row[2]}")
    finally:
        con.close()

if __name__ == "__main__":
    search_adani()
