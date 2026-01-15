from database import SessionLocal
from sqlalchemy import text
import logging

def check_indices():
    session = SessionLocal()
    try:
        # Check all distinct symbols
        query = text("SELECT DISTINCT symbol FROM stock_candles LIMIT 100")
        result = session.execute(query)
        symbols = [row[0] for row in result]
        print(f"Sample symbols in DB: {symbols[:20]}")
        
        # Look for NIFTY or VIX specifically
        print("\nSearching for indices...")
        query = text("SELECT DISTINCT symbol FROM stock_candles WHERE symbol ILIKE '%NIFTY%' OR symbol ILIKE '%INDEX%' OR symbol ILIKE '%VIX%'")
        result = session.execute(query)
        indices = [row[0] for row in result]
        print(f"Found index symbols: {indices}")
        
        if not indices:
            # Check stock_master too
            print("\nChecking stock_master...")
            query = text("SELECT symbol, instrument_key FROM stock_master WHERE symbol ILIKE '%NIFTY%' OR symbol ILIKE '%VIX%' LIMIT 20")
            result = session.execute(query)
            master = [(row[0], row[1]) for row in result]
            print(f"Symbols in stock_master: {master}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == '__main__':
    check_indices()
