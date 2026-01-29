import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from config import settings
from models_alpha import InstrumentMaster, StockCandle
from sqlalchemy.orm import sessionmaker

def debug_top5():
    engine = create_engine(settings.SYNC_DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        cutoff_date = datetime.now() - timedelta(days=100)
        print(f"Cutoff: {cutoff_date}")
        
        query = session.query(
            InstrumentMaster.symbol,
            StockCandle.candle_ts.label('timestamp'),
            StockCandle.open,
            StockCandle.high,
            StockCandle.low,
            StockCandle.close,
            StockCandle.volume
        ).join(
            InstrumentMaster, 
            StockCandle.instrument_id == InstrumentMaster.instrument_id
        ).filter(
            StockCandle.timeframe == 1440,
            StockCandle.candle_ts >= cutoff_date
        ).statement
        
        df = pd.read_sql(query, session.bind)
        print(f"Total rows fetched: {len(df)}")
        
        if df.empty:
            print("No data found!")
            return

        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['close'] = df['close'].astype(float)
        df = df.sort_values(['symbol', 'timestamp'])
        
        g = df.groupby('symbol')
        df['ema_9'] = g['close'].transform(lambda x: x.ewm(span=9, adjust=False).mean())
        df['ema_21'] = g['close'].transform(lambda x: x.ewm(span=21, adjust=False).mean())
        
        latest = df.groupby('symbol').tail(1).copy()
        print(f"Unique symbols in latest: {len(latest)}")
        
        buy_cond = (latest['ema_9'] > latest['ema_21']) & (latest['close'] > latest['ema_9'])
        sell_cond = (latest['ema_9'] < latest['ema_21']) & (latest['close'] < latest['ema_9'])
        
        print(f"Buy conditions met: {buy_cond.sum()}")
        print(f"Sell conditions met: {sell_cond.sum()}")
        
        if buy_cond.sum() > 0:
            print("Example Buy Candidate:")
            print(latest[buy_cond].head(1)[['symbol', 'close', 'ema_9', 'ema_21']])
            
        # Check why it might be failing in the actual scanner
        # Scanning score logic
        latest['action'] = np.where(buy_cond, 'BUY', np.where(sell_cond, 'SELL', 'HOLD'))
        latest['score'] = 50
        
        # In the original scanner, they might have other filters
        # Let's re-examine top5_buysell.py
        
    finally:
        session.close()

if __name__ == "__main__":
    debug_top5()
