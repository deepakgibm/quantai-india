"""
Daily Update Loader for Nifty 100
Checks for missing daily data in nifty100_daily table and fetches it from Upstox.
Designed to be run daily (e.g., via cron or scheduler) after market close.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Remove backend dir from sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) in sys.path:
    sys.path.remove(str(backend_dir))

from database import AsyncSessionLocal
from models_ml import Nifty100Daily
from models_alpha import ETLLog
from services.upstox_client import get_upstox_client
from config import settings

class Nifty100DailyUpdater:
    def __init__(self):
        self.client = get_upstox_client()
        self.stats = {
            "processed": 0,
            "updated": 0,
            "records_inserted": 0,
            "errors": 0,
            "up_to_date": 0
        }

    async def get_last_date(self, symbol: str, session):
        """Get the latest timestamp for a symbol from the database"""
        stmt = select(func.max(Nifty100Daily.timestamp)).where(Nifty100Daily.symbol == symbol)
        result = await session.execute(stmt)
        return result.scalar()

    async def fetch_and_update(self, symbol: str, instrument_key: str, last_date: datetime, session):
        # Determine date range
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if not last_date:
            # If no data exists, we should technically run the initial loader, 
            # but here we'll just fetch a small default window or log a warning
            print(f"  ⚠ No existing data for {symbol}. Fetching last 30 days.")
            from_date = today - timedelta(days=30)
        else:
            from_date = last_date + timedelta(days=1)
        
        if from_date >= today + timedelta(days=1):
            print(f"  ✓ {symbol} is up to date.")
            self.stats["up_to_date"] += 1
            return

        print(f"  Fetching {symbol} from {from_date.date()} to {today.date()}...")
        
        try:
            df = await self.client.get_historical_data(
                symbol=symbol,
                instrument_key=instrument_key,
                from_date=from_date,
                to_date=today,
                interval="1day"  # Daily candles
            )
            
            if df.empty:
                print(f"  No new data for {symbol}")
                return

            from sqlalchemy.dialects.postgresql import insert as pg_insert
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert
            import pandas as pd

            dialect_name = session.bind.dialect.name
            insert_fn = pg_insert if dialect_name == "postgresql" else sqlite_insert

            values_list = []
            for _, row in df.iterrows():
                ts = row['timestamp']
                if hasattr(ts, "to_pydatetime"):
                    ts = ts.to_pydatetime()
                if hasattr(ts, "tzinfo") and ts.tzinfo is not None:
                    ts = ts.replace(tzinfo=None)
                
                values_list.append({
                    "symbol": symbol,
                    "timestamp": ts,
                    "open": float(row['open']),
                    "high": float(row['high']),
                    "low": float(row['low']),
                    "close": float(row['close']),
                    "volume": int(row['volume']),
                    "source": "upstox"
                })

            inserted = 0
            if values_list:
                stmt = insert_fn(Nifty100Daily).values(values_list)
                stmt = stmt.on_conflict_do_nothing(index_elements=['symbol', 'timestamp'])
                res = await session.execute(stmt)
                await session.commit()
                inserted = res.rowcount if res.rowcount is not None and res.rowcount >= 0 else len(values_list)
            
            if inserted > 0:
                print(f"  ✓ {symbol}: Added/processed {inserted} records")
                self.stats["updated"] += 1
                self.stats["records_inserted"] += inserted
            else:
                print(f"  ✓ {symbol}: No new unique records")

        except Exception as e:
            print(f"  ✗ Error updating {symbol}: {e}")
            self.stats["errors"] += 1

    async def run(self):
        print("Starting Nifty 100 Daily Update (Upstox)...")
        start_time = datetime.now()
        
        # Get Nifty 200 symbols (superset of Nifty 100) to get instrument keys
        # We need to map our NIFTY_100_SYMBOLS to instrument keys
        print("Fetching instrument keys...")
        all_symbols = await self.client.get_nifty_200_symbols()
        symbol_map = {s[0]: s[1] for s in all_symbols}
        
        async with AsyncSessionLocal() as session:
            # Create ETL Log
            etl_log = ETLLog(
                job_type="nifty100_daily_update",
                status="running",
                start_time=start_time,
                source="upstox"
            )
            session.add(etl_log)
            await session.commit()

            for i, symbol in enumerate(settings.NIFTY_100_SYMBOLS):
                print(f"[{i+1}/{len(settings.NIFTY_100_SYMBOLS)}] Checking {symbol}")
                
                if symbol not in symbol_map:
                    print(f"  ⚠ Instrument key not found for {symbol}, skipping.")
                    self.stats["errors"] += 1
                    continue
                
                last_date = await self.get_last_date(symbol, session)
                await self.fetch_and_update(symbol, symbol_map[symbol], last_date, session)
                
                # Rate limit
                await asyncio.sleep(0.2)

            # Update ETL Log
            etl_log.status = "success" if self.stats["errors"] == 0 else "partial"
            etl_log.end_time = datetime.now()
            etl_log.records_inserted = self.stats["records_inserted"]
            etl_log.duration_seconds = (datetime.now() - start_time).total_seconds()
            await session.commit()

        print("\n" + "="*50)
        print("Update Complete")
        print(f"Updated: {self.stats['updated']}")
        print(f"Up to Date: {self.stats['up_to_date']}")
        print(f"Records Inserted: {self.stats['records_inserted']}")
        print(f"Errors: {self.stats['errors']}")
        print("="*50)

if __name__ == "__main__":
    updater = Nifty100DailyUpdater()
    asyncio.run(updater.run())
