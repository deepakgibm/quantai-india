from database import SessionLocal
from sqlalchemy import text
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
            
            # Delete any existing entry for today to avoid conflict
            session.execute(text("DELETE FROM stock_candles WHERE symbol = :s AND timeframe = '1d' AND timestamp = :t"), 
                            {"s": name, "t": today})
            
            # Insert fresh
            query = text("""
                INSERT INTO stock_candles (symbol, instrument_key, timeframe, timestamp, open, high, low, close, volume)
                VALUES (:symbol, :instrument_key, :timeframe, :timestamp, :open, :high, :low, :close, :volume)
            """)
            session.execute(query, {
                "symbol": name,
                "instrument_key": f"MANUAL_INDEX|{name}",
                "timeframe": "1d",
                "timestamp": today,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": 0
            })
        session.commit()
        print("Seeding complete.")
    except Exception as e:
        print(f"Error seeding DB: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == '__main__':
    seed_indices()
