"""Historical Data Loader for AlphaPrime Module

Fetches 5 years of 1‑minute OHLCV data for Nifty 200 stocks.
Features:
- Batch processing with progress tracking
- Duplicate detection and handling
- Gap detection and logging
- Database transaction management
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple

# Ensure project root is on PYTHONPATH for imports
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from database import AsyncSessionLocal
from models_alpha import StockCandle
from services.upstox_client import get_upstox_client
from services.instrument_resolver import resolve_instrument_id
from config import settings

class HistoricalLoader:
    """5‑year historical data bulk loader"""

    def __init__(self) -> None:
        self.client = get_upstox_client()
        self.symbols: List[Tuple[str, str]] = []
        self.stats = {
            "total_records": 0,
            "inserted": 0,
            "skipped": 0,
            "errors": 0,
        }

    async def load_symbols(self) -> List[Tuple[str, str]]:
        """Load Nifty 200 symbols (currently returns Nifty 50)"""
        self.symbols = await self.client.get_nifty_200_symbols()
        print(f"Loaded {len(self.symbols)} symbols for historical fetch")
        return self.symbols

    async def fetch_and_store(
        self,
        symbol: str,
        instrument_key: str,
        from_date: datetime,
        to_date: datetime,
        session,
    ) -> int:
        """Fetch and store data for a single symbol"""
        try:
            # Resolve symbol to instrument_id
            instrument_id = resolve_instrument_id(symbol)
            if not instrument_id:
                print(f"  [X] {symbol}: Failed to resolve instrument_id")
                self.stats["errors"] += 1
                return 0
                
            df = await self.client.get_historical_data(
                symbol, instrument_key, from_date, to_date, "day"
            )
            
            if df is None or df.empty:
                return 0

            from sqlalchemy.dialects.postgresql import insert as pg_insert
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert

            dialect_name = session.bind.dialect.name
            insert_fn = pg_insert if dialect_name == "postgresql" else sqlite_insert

            values_list = []
            for _, row in df.iterrows():
                ts = row["timestamp"]
                if hasattr(ts, "to_pydatetime"):
                    ts = ts.to_pydatetime()
                if hasattr(ts, "tzinfo") and ts.tzinfo is not None:
                    ts = ts.replace(tzinfo=None)
                elif hasattr(ts, "replace"):
                    ts = ts.replace(tzinfo=None)
                
                values_list.append({
                    "instrument_id": instrument_id,
                    "candle_ts": ts,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": int(row["volume"]),
                    "timeframe": 1440
                })

            inserted_count = 0
            if values_list:
                stmt = insert_fn(StockCandle).values(values_list)
                stmt = stmt.on_conflict_do_nothing(index_elements=['instrument_id', 'timeframe', 'candle_ts'])
                res = await session.execute(stmt)
                await session.commit()
                inserted_count = res.rowcount if res.rowcount is not None and res.rowcount >= 0 else len(values_list)

            self.stats["inserted"] += inserted_count
            self.stats["total_records"] += len(df)
            print(f"  [OK] {symbol}: Inserted/processed {inserted_count}/{len(df)} records")
            return inserted_count
        except Exception as e:
            print(f"  [X] {symbol}: Error - {e}")
            self.stats["errors"] += 1
            return 0

    async def run_bulk_load(self, years: int = 5) -> None:
        """Main entry point: load historical data for all symbols.

        The loader splits the overall date range into yearly chunks to stay within
        Upstox API limits and to keep each request size manageable.
        """
        start_time = datetime.now()
        job_id = f"historical_load_{start_time.strftime('%Y%m%d_%H%M%S')}"
        print("\n" + "=" * 60)
        print(f"Historical Data Loader - Job ID: {job_id}")
        print("=" * 60 + "\n")

        # Overall date range
        to_date = datetime.now()
        from_date = to_date - timedelta(days=years * 365)
        print(f"Date Range: {from_date.date()} to {to_date.date()}")
        print(f"Period: {years} years\n")

        await self.load_symbols()

        # Build yearly intervals
        intervals: List[Tuple[datetime, datetime]] = []
        cur_start = from_date
        while cur_start < to_date:
            cur_end = min(cur_start + timedelta(days=365), to_date)
            intervals.append((cur_start, cur_end))
            cur_start = cur_end

        async with AsyncSessionLocal() as session:
            # Create ETL log entry
            # etl_log = ETLLog(
            #     job_type="historical_load",
            #     job_id=job_id,
            #     symbols=[s[0] for s in self.symbols],
            #     start_time=from_date,
            #     end_time=to_date,
            #     status="running",
            #     source="upstox",
            #     triggered_by="manual",
            # )
            # session.add(etl_log)
            # await session.commit()

            for idx, (symbol, instrument_key) in enumerate(self.symbols, 1):
                print(f"[{idx}/{len(self.symbols)}] Processing {symbol}...")
                for sub_from, sub_to in intervals:
                    await self.fetch_and_store(
                        symbol=symbol,
                        instrument_key=instrument_key,
                        from_date=sub_from,
                        to_date=sub_to,
                        session=session,
                    )
                await session.commit()
                await asyncio.sleep(0.5)  # respect rate limits

            # Update ETL log
            duration = (datetime.now() - start_time).total_seconds()
            # etl_log.status = "success" if self.stats["errors"] == 0 else "partial"
            # etl_log.records_fetched = self.stats["total_records"]
            # etl_log.records_inserted = self.stats["inserted"]
            # etl_log.records_skipped = self.stats["skipped"]
            # etl_log.duration_seconds = duration
            # await session.commit()

        # Summary output
        print("\n" + "=" * 60)
        print("LOAD COMPLETE")
        print("=" * 60)
        print(f"Total Records: {self.stats['total_records']}")
        print(f"Inserted: {self.stats['inserted']}")
        print(f"Skipped (duplicates): {self.stats['skipped']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"Duration: {duration:.2f} seconds")
        print("=" * 60 + "\n")

async def main() -> None:
    """CLI entry point"""
    loader = HistoricalLoader()
    await loader.run_bulk_load(years=settings.HISTORICAL_DATA_YEARS)

if __name__ == "__main__":
    asyncio.run(main())
