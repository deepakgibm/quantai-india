from datetime import datetime, timedelta
from sqlalchemy import create_engine
from config import settings
from models_alpha import InstrumentMaster, StockCandle
from sqlalchemy.orm import sessionmaker

def debug_bulk_query():
    engine = create_engine(settings.SYNC_DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        cutoff_date = datetime.now() - timedelta(days=100)
        print(f"Cutoff: {cutoff_date}")
        
        query = session.query(
            InstrumentMaster.symbol,
            StockCandle.candle_ts,
            StockCandle.close
        ).join(
            InstrumentMaster, 
            StockCandle.instrument_id == InstrumentMaster.instrument_id
        ).filter(
            StockCandle.timeframe == 1440,
            StockCandle.candle_ts >= cutoff_date
        )
        
        print(f"Query string: {query.statement}")
        
        results = query.limit(10).all()
        print(f"Result count (limited): {len(results)}")
        for r in results:
            print(f"  {r.symbol} | {r.candle_ts} | {r.close}")
            
        total_count = session.query(StockCandle).filter(StockCandle.timeframe == 1440).count()
        print(f"Total 1d candles: {total_count}")
        
        total_instrument = session.query(InstrumentMaster).count()
        print(f"Total instruments: {total_instrument}")
        
    finally:
        session.close()

if __name__ == "__main__":
    debug_bulk_query()
