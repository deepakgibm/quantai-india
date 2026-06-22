import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from sqlalchemy import create_engine, text
from config import settings

def main():
    engine = create_engine(settings.SYNC_DATABASE_URL)
    print("Database URL:", settings.DATABASE_URL)
    
    query = text("""
        SELECT im.symbol, count(*), min(sc.candle_ts), max(sc.candle_ts)
        FROM stock_candle sc
        JOIN instrument_master im ON sc.instrument_id = im.instrument_id
        WHERE im.symbol IN ('RELIANCE', 'NIFTY 50', 'Nifty 50')
          AND sc.timeframe = 1440
        GROUP BY im.symbol
    """)
    
    with engine.connect() as conn:
        res = conn.execute(query).fetchall()
        print("Candle counts:")
        for r in res:
            print(f"Symbol: {r[0]}, Count: {r[1]}, Min Date: {r[2]}, Max Date: {r[3]}")

if __name__ == "__main__":
    main()
