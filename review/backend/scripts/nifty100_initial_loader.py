"""
Initial Data Loader for Nifty 100 Daily Data
Fetches 20 years of history using yfinance and populates the nifty100_daily table.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import yfinance as yf
from sqlalchemy.exc import IntegrityError

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Remove backend dir from sys.path to prevent top-level imports
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) in sys.path:
    sys.path.remove(str(backend_dir))

from backend.database import AsyncSessionLocal, init_db
from backend.models_ml import Nifty100Daily
from backend.models_alpha import ETLLog
from backend.config import settings

class Nifty100InitialLoader:
    def __init__(self):
        self.symbols = settings.NIFTY_100_SYMBOLS
        self.stats = {
            "total_symbols": len(self.symbols),
            "processed": 0,
            "records_inserted": 0,
            "errors": 0
        }

    async def fetch_and_store(self, symbol: str, session):
        print(f"Fetching data for {symbol}...")
        try:
            # Append .NS for NSE stocks if not present
            ticker_symbol = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
            
            # Fetch 20 years of data
            # Run yfinance in a separate thread to avoid blocking asyncio loop
            ticker = yf.Ticker(ticker_symbol)
            hist = await asyncio.to_thread(ticker.history, period="20y", interval="1d")
            
            if hist.empty:
                print(f"  No data found for {symbol}")
                return

            records = []
            for date, row in hist.iterrows():
                record = Nifty100Daily(
                    symbol=symbol,
                    timestamp=date,
                    open=row['Open'],
                    high=row['High'],
                    low=row['Low'],
                    close=row['Close'],
                    volume=row['Volume'],
                    source="yfinance"
                )
                records.append(record)

            # Bulk insert chunks to avoid memory issues
            chunk_size = 1000
            for i in range(0, len(records), chunk_size):
                chunk = records[i:i + chunk_size]
                session.add_all(chunk)
                try:
                    await session.commit()
                    self.stats["records_inserted"] += len(chunk)
                except IntegrityError:
                    await session.rollback()
                    # Fallback to individual insert for duplicates
                    for rec in chunk:
                        try:
                            session.add(rec)
                            await session.commit()
                            self.stats["records_inserted"] += 1
                        except IntegrityError:
                            await session.rollback()
            
            print(f"  ✓ {symbol}: Processed {len(records)} records")
            self.stats["processed"] += 1

        except Exception as e:
            print(f"  ✗ Error fetching {symbol}: {e}")
            self.stats["errors"] += 1

    async def run(self):
        print("Starting Nifty 100 Initial Load (20 Years)...")
        await init_db() # Ensure tables exist
        start_time = datetime.now()
        
        async with AsyncSessionLocal() as session:
            # Create ETL Log
            etl_log = ETLLog(
                job_type="nifty100_initial_load",
                status="running",
                start_time=start_time,
                source="yfinance"
            )
            session.add(etl_log)
            await session.commit()

            for i, symbol in enumerate(self.symbols):
                print(f"[{i+1}/{len(self.symbols)}] Processing {symbol}")
                await self.fetch_and_store(symbol, session)
                # Small delay to be nice to Yahoo
                await asyncio.sleep(1)

            # Update ETL Log
            etl_log.status = "success" if self.stats["errors"] == 0 else "partial"
            etl_log.end_time = datetime.now()
            etl_log.records_inserted = self.stats["records_inserted"]
            etl_log.duration_seconds = (datetime.now() - start_time).total_seconds()
            await session.commit()

        print("\n" + "="*50)
        print("Load Complete")
        print(f"Symbols Processed: {self.stats['processed']}/{self.stats['total_symbols']}")
        print(f"Records Inserted: {self.stats['records_inserted']}")
        print(f"Errors: {self.stats['errors']}")
        print("="*50)

if __name__ == "__main__":
    loader = Nifty100InitialLoader()
    asyncio.run(loader.run())
