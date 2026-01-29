from backend.database import SessionLocal
from sqlalchemy import text

def check_counts():
    session = SessionLocal()
    try:
        print("Checking counts in current schema...")
        
        # Check instrument_master
        try:
            res = session.execute(text("SELECT COUNT(*) FROM instrument_master"))
            print(f"instrument_master count: {res.scalar()}")
        except Exception as e:
            session.rollback()
            print(f"instrument_master table issue: {e}")
            
        # Check stock_candle (new partitioned table)
        try:
            res = session.execute(text("SELECT COUNT(*) FROM stock_candle"))
            print(f"stock_candle count: {res.scalar()}")
        except Exception as e:
            session.rollback()
            print(f"stock_candle table issue: {e}")

        # Check legacy stock_candles if it exists
        try:
            res = session.execute(text("SELECT COUNT(*) FROM stock_candles"))
            print(f"Legacy stock_candles count: {res.scalar()}")
        except Exception as e:
            session.rollback()
            print(f"Legacy stock_candles table issue: {e}")

        # Check Suzlon specifically
        print("\nChecking SUZLON specifically...")
        try:
            res = session.execute(text("""
                SELECT im.instrument_id, im.symbol, COUNT(sc.candle_ts) 
                FROM instrument_master im
                LEFT JOIN stock_candle sc ON im.instrument_id = sc.instrument_id
                WHERE im.symbol = 'SUZLON'
                GROUP BY im.instrument_id, im.symbol
            """))
            row = res.fetchone()
            if row:
                print(f"SUZLON: ID={row[0]}, Symbol={row[1]}, Candle Count={row[2]}")
            else:
                print("SUZLON not found in instrument_master")
        except Exception as e:
            session.rollback()
            print(f"Error checking SUZLON: {e}")

        # Check top 10 symbols by candle count
        print("\nTop 10 symbols by candle count in stock_candle (last 30 days):")
        try:
            res = session.execute(text("""
                SELECT im.symbol, COUNT(sc.candle_ts) as count
                FROM instrument_master im
                JOIN stock_candle sc ON im.instrument_id = sc.instrument_id
                WHERE sc.candle_ts > NOW() - INTERVAL '30 days'
                GROUP BY im.symbol
                ORDER BY count DESC
                LIMIT 10
            """))
            for row in res:
                print(f"- {row[0]}: {row[1]} candles")
        except Exception as e:
            session.rollback()
            print(f"Error checking top 10: {e}")

        # Check symbols with 0 candles
        print("\nSymbols with 0 candles in stock_candle:")
        try:
            res = session.execute(text("""
                SELECT im.symbol
                FROM instrument_master im
                LEFT JOIN stock_candle sc ON im.instrument_id = sc.instrument_id
                WHERE sc.instrument_id IS NULL
                LIMIT 20
            """))
            for row in res:
                print(f"- {row[0]}")
        except Exception as e:
            session.rollback()
            print(f"Error checking 0 candles: {e}")

        # Check Suzlon timeframe distribution
        print("\nChecking timeframe distribution for SUZLON:")
        try:
            res = session.execute(text("""
                SELECT timeframe, COUNT(*) 
                FROM stock_candle sc
                JOIN instrument_master im ON sc.instrument_id = im.instrument_id
                WHERE im.symbol = 'SUZLON'
                GROUP BY timeframe
                ORDER BY timeframe
            """))
            for row in res:
                print(f"- TF {row[0]}: {row[1]} candles")
        except Exception as e:
            session.rollback()
            print(f"Error checking SUZLON TF: {e}")

        # Global timeframe stats
        print("\nGlobal timeframe stats:")
        try:
            res = session.execute(text("""
                SELECT timeframe, COUNT(*), COUNT(DISTINCT instrument_id)
                FROM stock_candle
                GROUP BY timeframe
                ORDER BY timeframe
            """))
            for row in res:
                print(f"- TF {row[0]}: {row[1]} candles for {row[2]} symbols")
        except Exception as e:
            session.rollback()
            print(f"Error checking global TF: {e}")

        # Check for symbols missing daily data
        print("\nSymbols missing daily data (timeframe=1440):")
        try:
            res = session.execute(text("""
                SELECT symbol FROM instrument_master
                WHERE instrument_id NOT IN (
                    SELECT DISTINCT instrument_id FROM stock_candle WHERE timeframe = 1440
                )
                LIMIT 20
            """))
            for row in res:
                print(f"- {row[0]}")
        except Exception as e:
            session.rollback()
            print(f"Error checking missing daily: {e}")

    except Exception as e:
        print(f"General Error: {e}")
    finally:
        session.close()

if __name__ == '__main__':
    check_counts()
