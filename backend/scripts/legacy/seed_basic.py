from database import SessionLocal
from models_alpha import StockCandle
from services.instrument_resolver import resolve_instrument_id
from datetime import datetime

def seed():
    session = SessionLocal()
    try:
        data = [
            ('NIFTY 50', '25683.30'),
            ('BANK NIFTY', '59251.55'),
            ('SENSEX', '83576.0'),
            ('INDIA VIX', '10.93')
        ]
        
        for symbol, price in data:
            instrument_id = resolve_instrument_id(symbol)
            if not instrument_id:
                print(f"Skipping {symbol}: could not resolve instrument_id")
                continue
                
            # Delete existing for today/symbol
            session.query(StockCandle).filter(
                StockCandle.instrument_id == instrument_id,
                StockCandle.timeframe == 1440,
                StockCandle.candle_ts >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            ).delete()
            
            candle = StockCandle(
                instrument_id=instrument_id,
                timeframe=1440,
                candle_ts=datetime.now(),
                open=float(price),
                high=float(price),
                low=float(price),
                close=float(price),
                volume=0
            )
            session.add(candle)
            
        session.commit()
        print("Success")
    except Exception as e:
        print(f"Fail: {e}")
        session.rollback()
    finally:
        session.close()

seed()
