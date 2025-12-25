"""
Simple Nifty 100 Data Loader
Loads 20 years of historical data for testing
"""
import asyncio
import yfinance as yf
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import IntegrityError

# Database connection
DATABASE_URL = "sqlite+aiosqlite:///./quantai.db"

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Define model directly
Base = declarative_base()

class Nifty100Daily(Base):
    __tablename__ = "nifty100_daily"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    source = Column(String(20), nullable=False, default="yfinance")

# Top 10 Nifty symbols for quick test
TEST_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK"
]

async def load_symbol(symbol: str, session):
    """Load 20 years of data for one symbol"""
    print(f"Loading {symbol}...")
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        hist = await asyncio.to_thread(ticker.history, period="20y", interval="1d")
        
        if hist.empty:
            print(f"  No data for {symbol}")
            return 0
        
        count = 0
        for date, row in hist.iterrows():
            record = Nifty100Daily(
                symbol=symbol,
                timestamp=date,
                open=float(row['Open']),
                high=float(row['High']),
                low=float(row['Low']),
                close=float(row['Close']),
                volume=int(row['Volume']),
                source="yfinance"
            )
            session.add(record)
            count += 1
        
        await session.commit()
        print(f"  ✓ {symbol}: {count} records loaded")
        return count
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        await session.rollback()
        return 0

async def main():
    print("="*60)
    print("Quick Nifty 100 Data Loader (Top 10 Symbols)")
    print("="*60)
    print()
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    total_records = 0
    async with AsyncSessionLocal() as session:
        for i, symbol in enumerate(TEST_SYMBOLS, 1):
            print(f"[{i}/{len(TEST_SYMBOLS)}]", end=" ")
            count = await load_symbol(symbol, session)
            total_records += count
            await asyncio.sleep(0.5)  # Be nice to Yahoo
    
    print()
    print("="*60)
    print(f"Loading Complete!")
    print(f"Total records loaded: {total_records:,}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
