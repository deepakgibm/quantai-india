from database import SessionLocal
from sqlalchemy import text
from datetime import datetime

def seed():
    session = SessionLocal()
    try:
        # Delete first to be safe
        session.execute(text("DELETE FROM stock_candles WHERE symbol IN ('NIFTY 50', 'BANK NIFTY', 'INDIA VIX', 'SENSEX')"))
        
        data = [
            ('NIFTY 50', 'NSE_INDEX|Nifty 50', '25683.30'),
            ('BANK NIFTY', 'NSE_INDEX|Nifty Bank', '59251.55'),
            ('SENSEX', 'BSE_INDEX|SENSEX', '83576.0'),
            ('INDIA VIX', 'NSE_INDEX|India VIX', '10.93')
        ]
        
        for sym, key, price in data:
            session.execute(text(f"INSERT INTO stock_candles (symbol, instrument_key, timeframe, timestamp, close, open, high, low, volume) VALUES ('{sym}', '{key}', '1d', NOW(), {price}, {price}, {price}, {price}, 0)"))
            
        session.commit()
        print("Success")
    except Exception as e:
        print(f"Fail: {e}")
        session.rollback()
    finally:
        session.close()

seed()
