"""
Nifty 200 Multi-Interval Data Loader (Standalone)
Loads 1min, 3min, 5min, 15min, 30min data from Jan 2022 using Upstox
"""
import asyncio
import yfinance as yf
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import IntegrityError

# Database  
DATABASE_URL = "sqlite+aiosqlite:///./quantai.db"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Model
Base = declarative_base()

class StockData(Base):
    __tablename__ = "stock_data"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    interval = Column(String(10))
    source = Column(String(20), default="yfinance")

# Top 20 Nifty stocks (as placeholder for full 200)
NIFTY_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK",
    "LTIM", "LT", "AXISBANK", "HCLTECH", "BAJFINANCE",
    "ASIANPAINT", "MARUTI", "SUNPHARMA", "TITAN", "ULTRACEMCO"
]

# Intervals to load
INTERVALS = {
    "1min": "1m",
    "3min": "3m",  # Note: yfinance doesn't support 3min, we'll use 5min
    "5min": "5m",
    "15min": "15m",
    "30min": "30m"
}

async def load_interval_data(symbol: str, interval_name: str, yf_interval: str, session):
    """Load data for one symbol, one interval"""
    print(f"      {interval_name:6s}", end=" ")
    
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        
        # yfinance can only go back 60 days for 1m, 5m
        # Use different periods for different intervals
        if yf_interval in ["1m", "5m"]:
            period = "60d"  # Max for minute data
        elif yf_interval in ["15m", "30m"]:
            period = "60d"
        else:
            period = "max"
        
        hist = await asyncio.to_thread(
            ticker.history,
            period=period,
            interval=yf_interval
        )
        
        if hist.empty:
            print("No data")
            return 0
        
        count = 0
        for date, row in hist.iterrows():
            record = StockData(
                symbol=symbol,
                timestamp=date,
                open=float(row['Open']),
                high=float(row['High']),
                low=float(row['Low']),
                close=float(row['Close']),
                volume=int(row['Volume']),
                interval=interval_name,
                source="yfinance"
            )
            try:
                session.add(record)
                count += 1
            except:
                pass
        
        await session.commit()
        print(f"✓ {count:,} records")
        return count
        
    except Exception as e:
        print(f"✗ {e}")
        await session.rollback()
        return 0

async def main():
    print("\n" + "="*80)
    print("NIFTY STOCKS MULTI-INTERVAL DATA LOADER")
    print("="*80)
    print()
    print(f"📊 Symbols: {len(NIFTY_SYMBOLS)} stocks")
    print(f"⏱️  Intervals: {', '.join(INTERVALS.keys())}")
    print("⚠️  Note: Using yfinance (limited to ~60 days for minute data)")
    print("⚠️  For full historical data, need Upstox API with proper credentials")
    print()
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    total_records = 0
    async with AsyncSessionLocal() as session:
        for idx, symbol in enumerate(NIFTY_SYMBOLS, 1):
            print(f"[{idx}/{len(NIFTY_SYMBOLS)}] {symbol}")
            
            for interval_name, yf_interval in INTERVALS.items():
                if interval_name == "3min":
                    print(f"      3min   ⏭️  Skipped (not supported by yfinance)")
                    continue
                
                count = await load_interval_data(symbol, interval_name, yf_interval, session)
                total_records += count
                await asyncio.sleep(0.2)
            
            print()
    
    print("="*80)
    print(f"✅ Load Complete!")
    print(f"✅ Total Records: {total_records:,}")
    print("="*80)
    print()
    print("📝 IMPORTANT NOTE:")
    print("   This used yfinance which only provides ~60 days of intraday data.")
    print("   For full historical data from Jan 2022, you need:")
    print("   1. Valid Upstox API credentials")
    print("   2. Full Nifty 200 instrument key mapping")
    print("   3. Use the proper Upstox loader script")
    print()

if __name__ == "__main__":
    asyncio.run(main())
