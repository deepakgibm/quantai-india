from database import SessionLocal
from sqlalchemy import text

def check_data():
    session = SessionLocal()
    try:
        print("Checking counts...")
        res = session.execute(text("SELECT COUNT(*) FROM stock_master"))
        print(f"stock_master count: {res.scalar()}")
        res = session.execute(text("SELECT COUNT(*) FROM stock_candles"))
        print(f"stock_candles count: {res.scalar()}")
        try:
            res = session.execute(text("SELECT COUNT(*) FROM stock_data"))
            print(f"stock_data count: {res.scalar()}")
        except:
            print("stock_data table does not exist")

        print("\nChecking timeframes in stock_candles...")
        res = session.execute(text("SELECT DISTINCT timeframe FROM stock_candles"))
        for row in res:
            print(f"Timeframe: '{row[0]}'")
            
        print("\nChecking sample data in stock_master...")
        res = session.execute(text("SELECT symbol, company_name FROM stock_master LIMIT 5"))
        for row in res:
            print(f"Master sample: Symbol='{row[0]}', Name='{row[1]}'")

        print("\nChecking samples in stock_candles...")
        res = session.execute(text("SELECT symbol, timeframe, timestamp FROM stock_candles LIMIT 5"))
        for row in res:
            print(f"Candle sample: Symbol='{row[0]}', TF='{row[1]}', TS='{row[2]}'")

        print("\nChecking indices in stock_master...")
        res = session.execute(text("SELECT symbol, company_name, instrument_key FROM stock_master WHERE symbol LIKE '%NIFTY%' OR symbol LIKE '%VIX%' OR instrument_key LIKE '%INDEX%'"))
        for row in res:
            print(f"Index in master: Symbol='{row[0]}', Name='{row[1]}', Key='{row[2]}'")
            
        print("\nSearching for Index symbols in stock_data...")
        try:
            res = session.execute(text("SELECT DISTINCT symbol FROM stock_data WHERE symbol ILIKE '%NIFTY%' OR symbol ILIKE '%Index%' LIMIT 20"))
            for row in res:
                print(f"stock_data index: Symbol='{row[0]}'")
        except:
            pass

        print("\nChecking indices in stock_candles...")
        indices = ["NIFTY 50", "BANK NIFTY", "INDIA VIX"]
        for index in indices:
            res = session.execute(text("SELECT COUNT(*) FROM stock_candles WHERE symbol = :symbol"), {"symbol": index})
            count = res.scalar()
            print(f"Index '{index}': {count} rows")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == '__main__':
    check_data()
