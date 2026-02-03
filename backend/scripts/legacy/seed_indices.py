from database import SessionLocal
from models_alpha import StockCandle
from services.instrument_resolver import resolve_instrument_id
from datetime import datetime

def seed_indices():
    indices = [
        ("NIFTY 50", 25683.30, -192.6), # -0.75% approximately
        ("BANK NIFTY", 59251.55, -450.0),
        ("INDIA VIX", 10.93, 0.32),
        ("SENSEX", 83576.0, -600.0)
    ]
    
    session = SessionLocal()
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for name, price, change in indices:
            print(f"Seeding {name}: {price}")
            
            instrument_id = resolve_instrument_id(name)
            if not instrument_id:
                print(f"Skipping {name}: could not resolve instrument_id")
                continue

            # Delete any existing entry for today to avoid conflict
            session.query(StockCandle).filter(
                StockCandle.instrument_id == instrument_id,
                StockCandle.timeframe == 1440,
                StockCandle.candle_ts >= today
            ).delete()
            
            # Insert fresh
            candle = StockCandle(
                instrument_id=instrument_id,
                timeframe=1440,
                candle_ts=today,
                open=float(price),
                high=float(price),
                low=float(price),
                close=float(price),
                volume=0
            )
            session.add(candle)
            
        session.commit()
        print("Seeding complete.")
    except Exception as e:
        print(f"Error seeding DB: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == '__main__':
    seed_indices()
