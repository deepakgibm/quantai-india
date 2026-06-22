import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from sqlalchemy import create_engine, text
from config import settings

def main():
    engine = create_engine(settings.SYNC_DATABASE_URL)
    cutoff = datetime.now() - timedelta(days=45)
    print("Cutoff Date:", cutoff)
    
    with engine.connect() as conn:
        # Stock
        stock_query = text("""
            SELECT sc.candle_ts as timestamp, sc.close
            FROM stock_candle sc
            JOIN instrument_master im ON sc.instrument_id = im.instrument_id
            WHERE im.symbol = 'RELIANCE' AND sc.timeframe = 1440 AND sc.candle_ts >= :cutoff
            ORDER BY sc.candle_ts ASC
        """)
        stock_rows = conn.execute(stock_query, {"cutoff": cutoff}).fetchall()
        print(f"RELIANCE rows count: {len(stock_rows)}")
        if stock_rows:
            print("RELIANCE sample (first & last):", stock_rows[0], "...", stock_rows[-1])
            
        # Nifty
        nifty_query = text("""
            SELECT sc.candle_ts as timestamp, sc.close
            FROM stock_candle sc
            JOIN instrument_master im ON sc.instrument_id = im.instrument_id
            WHERE im.symbol = 'NIFTY 50' AND sc.timeframe = 1440 AND sc.candle_ts >= :cutoff
            ORDER BY sc.candle_ts ASC
        """)
        nifty_rows = conn.execute(nifty_query, {"cutoff": cutoff}).fetchall()
        print(f"NIFTY 50 rows count: {len(nifty_rows)}")
        if nifty_rows:
            print("NIFTY 50 sample (first & last):", nifty_rows[0], "...", nifty_rows[-1])

if __name__ == "__main__":
    main()
