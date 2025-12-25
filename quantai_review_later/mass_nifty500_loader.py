"""
Mass Nifty 500 Data Loader (Isolated Mode)
Loads data for all Nifty 500 stocks across multiple timeframes.
Uses LOCAL SQLAlchemy models to avoid conflicts with application's ORM registry.

Strategy:
- 1 Day: Last 3 Years -> nifty100_daily
- 1 Min: Last 30 Days -> stock_data
- 3 Min: Resampled from 1 Min -> intraday_candles
- 5, 15, 30 Min: Last 60 Days -> intraday_candles
"""

import sys
import asyncio
import traceback
import pandas as pd
import yfinance as yf
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Index
from sqlalchemy.orm import sessionmaker, declarative_base
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from services.nifty500_fetcher import Nifty500Fetcher

# Configuration
MAX_WORKERS = 1  # Sequential to avoid DB locking
DAYS_DAILY = 365 * 3
DAYS_1MIN = 30
DAYS_INTRADAY = 60

# --- LOCAL MODEL DEFINITIONS (ISOLATED) ---
LocalBase = declarative_base()

class LocalNifty100Daily(LocalBase):
    __tablename__ = "nifty100_daily"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20))
    timestamp = Column(DateTime)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    source = Column(String(20), default="yfinance")

class LocalStockData(LocalBase):
    __tablename__ = "stock_data"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20))
    timestamp = Column(DateTime)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    interval = Column(String(10), default="1min")
    source = Column(String(20), default="yfinance")

class LocalIntradayCandle(LocalBase):
    __tablename__ = "intraday_candles"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(50))
    timestamp = Column(DateTime)
    interval = Column(String(10))
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    source = Column(String(20), default="upstox")

# --- END LOCAL MODELS ---

def get_nifty500_symbols():
    """Get list of Nifty 500 symbols"""
    try:
        fetcher = Nifty500Fetcher()
        # Try fetching fresh list
        df = fetcher.fetch_from_nse()
        if not df.empty:
            fetcher.save_to_database(df)
            return df['Symbol'].tolist()
        
        # Fallback to DB
        print("⚠️ Using existing symbols from database")
        symbols = fetcher.get_all_symbols()
        return [s[0] for s in symbols]
    except Exception as e:
        print(f"⚠️ Error fetching symbols: {e}")
        return []

def save_daily_data(session, symbol, df):
    """Save daily data to nifty100_daily"""
    count = 0
    for idx, row in df.iterrows():
        obj = LocalNifty100Daily(
            symbol=symbol,
            timestamp=idx.to_pydatetime().replace(tzinfo=None),
            open=float(row['Open']),
            high=float(row['High']),
            low=float(row['Low']),
            close=float(row['Close']),
            volume=int(row['Volume'])
        )
        session.merge(obj)
        count += 1
    return count

def save_1min_data(session, symbol, df):
    """Save 1-min data to stock_data"""
    count = 0
    for idx, row in df.iterrows():
        obj = LocalStockData(
            symbol=symbol,
            timestamp=idx.to_pydatetime().replace(tzinfo=None),
            open=float(row['Open']),
            high=float(row['High']),
            low=float(row['Low']),
            close=float(row['Close']),
            volume=int(row['Volume']),
            interval='1m' 
        )
        session.merge(obj)
        count += 1
    return count

def save_intraday_data(session, symbol, df, interval):
    """Save intraday data to intraday_candles"""
    count = 0
    for idx, row in df.iterrows():
        obj = LocalIntradayCandle(
            symbol=symbol,
            timestamp=idx.to_pydatetime().replace(tzinfo=None),
            open=float(row['Open']),
            high=float(row['High']),
            low=float(row['Low']),
            close=float(row['Close']),
            volume=int(row['Volume']),
            interval=interval
        )
        session.merge(obj)
        count += 1
    return count

def process_symbol(symbol):
    """Process all timeframes for a single symbol"""
    results = {
        'symbol': symbol, 
        '1d': 0, '1m': 0, '3m': 0, 
        '5m': 0, '15m': 0, '30m': 0,
        'status': 'success'
    }
    
    engine = create_engine(
        settings.DATABASE_URL.replace("+aiosqlite", ""),
        connect_args={"check_same_thread": False}
    )
    Session = sessionmaker(bind=engine)
    session = Session()
    
    ticker_name = f"{symbol}.NS"
    ticker = yf.Ticker(ticker_name)
    
    try:
        # 1. Daily Data (3 Years)
        df_daily = ticker.history(period=f"{DAYS_DAILY//365}y", interval="1d")
        if not df_daily.empty:
            results['1d'] = save_daily_data(session, symbol, df_daily)
            
        # 2. 1-Min Data (30 Days)
        df_1m = ticker.history(period="1mo", interval="1m")
        if not df_1m.empty:
            results['1m'] = save_1min_data(session, symbol, df_1m)
            
            # 3. 3-Min Data
            df_3m = df_1m.resample('3min').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            
            if not df_3m.empty:
                results['3m'] = save_intraday_data(session, symbol, df_3m, '3m')
        
        # 4. Other Intraday
        for interval in ['5m', '15m', '30m']:
            df = ticker.history(period="60d", interval=interval)
            if not df.empty:
                results[interval] = save_intraday_data(session, symbol, df, interval)
        
        session.commit()
        
    except Exception as e:
        session.rollback()
        results['status'] = f"Error: {str(e)}"
        # print(f"❌ {symbol}: {traceback.format_exc()}")
    finally:
        session.close()
        engine.dispose()
        
    return results

import json

CHECKPOINT_FILE = Path(__file__).parent.parent / "loader_checkpoint.json"

def load_checkpoint():
    """Load checkpoint from file"""
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"last_symbol_index": 0}

def save_checkpoint(index):
    """Save checkpoint to file"""
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({"last_symbol_index": index}, f)

def main():
    print("="*70)
    print("🚀 NIFTY 500 MASS DATA LOADER (Isolated Mode)")
    print("="*70)
    
    # 1. Get Symbols
    print("\nStep 1: Fetching Symbols...")
    try:
        symbols = get_nifty500_symbols()
        if not symbols:
            # Fallback if fetcher fails completely
            print("⚠️ Using fallback symbol list")
            symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"]
    except Exception as e:
        print(f"❌ Error getting symbols: {e}")
        return
        
    print(f"✅ Found {len(symbols)} symbols")
    
    # Filter out PRO/indices if any
    symbols = [s for s in symbols if "NIFTY" not in s]
    
    # 2. Load checkpoint and resume
    checkpoint = load_checkpoint()
    start_index = checkpoint.get("last_symbol_index", 0)
    
    if start_index > 0:
        print(f"\n📍 RESUMING from symbol index {start_index} (skipping {start_index} already processed)")
        symbols = symbols[start_index:]
    
    # 3. Process
    print(f"\nStep 2: Processing {len(symbols)} remaining symbols with {MAX_WORKERS} workers...")
    print("This will take a while. Progress will be shown below.\n")
    
    total_records = 0
    start_time = datetime.now()
    current_index = start_index
    
    for sym in symbols:
        try:
            res = process_symbol(sym)
            current_index += 1
            
            if res['status'] == 'success':
                total_sym_records = sum(v for k,v in res.items() if isinstance(v, int))
                total_records += total_sym_records
                print(f"[{current_index:3}/{start_index + len(symbols)}] {sym:<12} ✅ {total_sym_records:5,} records "
                      f"(1d:{res['1d']}, 1m:{res['1m']}, 3m:{res['3m']}, 5m:{res['5m']}...)")
            else:
                print(f"[{current_index:3}/{start_index + len(symbols)}] {sym:<12} ❌ {res['status']}")
            
            # Save checkpoint after each symbol
            save_checkpoint(current_index)
            
        except Exception as e:
            print(f"[{current_index:3}/{start_index + len(symbols)}] {sym:<12} ❌ Exception: {e}")
            save_checkpoint(current_index)
                
    duration = datetime.now() - start_time
    print("\n" + "="*70)
    print("🏁 LOAD COMPLETE")
    print("="*70)
    print(f"Time Taken: {duration}")
    print(f"Total Records: {total_records:,}")
    
    # Clear checkpoint on successful completion
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        print("✅ Checkpoint cleared - full load complete!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user - checkpoint saved for resume")
