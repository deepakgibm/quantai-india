from database import SessionLocal
from sqlalchemy import text

def check_recency():
    s = SessionLocal()
    try:
        nifty_max = s.execute(text("SELECT MAX(timestamp) FROM nifty100_daily")).scalar()
        candle_max = s.execute(text("SELECT MAX(candle_ts) FROM stock_candle WHERE timeframe=1440")).scalar()
        print(f"Latest Nifty100Daily: {nifty_max}")
        print(f"Latest StockCandle 1d: {candle_max}")
    finally:
        s.close()

if __name__ == "__main__":
    check_recency()
