"""Weekly data loader for AlphaPrime module.

Loads one week of 1‑minute OHLCV data at a time, starting from 2020‑11‑23.
Tracks progress in a JSON file (load_tracker.json) so the process can be resumed
or inspected via the API.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple
from sqlalchemy.exc import IntegrityError

# Imports


from backend.database import AsyncSessionLocal
from backend.models_alpha import StockCandle, ETLLog
from backend.services.upstox_client import get_upstox_client
from backend.services.instrument_resolver import resolve_instrument_id

TRACKER_PATH = Path(__file__).with_name("load_tracker.json")

class WeeklyLoader:
    def __init__(self) -> None:
        self.client = get_upstox_client()
        self.symbols: List[Tuple[str, str]] = []
        self.stats = {"total_records": 0, "inserted": 0, "skipped": 0, "errors": 0}
        self.tracker = {
            "last_start": None,  # ISO date string of the week start that was just completed
            "last_end": None,    # ISO date string of the week end that was just completed
            "status": "pending",  # pending | loading | completed | error
            "current_symbol_index": 0,
            "total_symbols": 0,
        }
        self._load_tracker()

    def _load_tracker(self):
        if TRACKER_PATH.exists():
            try:
                with open(TRACKER_PATH, "r", encoding="utf-8") as f:
                    self.tracker.update(json.load(f))
            except Exception as e:
                print(f"Failed to read tracker file: {e}")
        else:
            # Initialize with first week start date
            self.tracker["last_start"] = None
            self.tracker["last_end"] = None
            self.tracker["status"] = "pending"
            self._save_tracker()

    def _save_tracker(self):
        try:
            with open(TRACKER_PATH, "w", encoding="utf-8") as f:
                json.dump(self.tracker, f, indent=2)
        except Exception as e:
            print(f"Failed to write tracker file: {e}")

    async def load_symbols(self) -> List[Tuple[str, str]]:
        self.symbols = await self.client.get_nifty_200_symbols()
        self.tracker["total_symbols"] = len(self.symbols)
        self._save_tracker()
        print(f"Loaded {len(self.symbols)} symbols for weekly fetch")
        return self.symbols

    async def fetch_and_store(
        self,
        symbol: str,
        instrument_key: str,
        from_date: datetime,
        to_date: datetime,
        session,
    ) -> int:
        try:
            df = await self.client.get_historical_data(
                symbol=symbol,
                instrument_key=instrument_key,
                from_date=from_date,
                to_date=to_date,
                interval="1minute",
            )
            if df.empty:
                print(f"  No data for {symbol} {from_date.date()}–{to_date.date()}")
                return 0
            # Resolve symbol to instrument_id
            instrument_id = resolve_instrument_id(symbol)
            if not instrument_id:
                print(f"  ✗ {symbol}: Failed to resolve instrument_id")
                self.stats["errors"] += 1
                return 0
                
            inserted = 0
            for _, row in df.iterrows():
                stock = StockCandle(
                    instrument_id=instrument_id,
                    candle_ts=row["timestamp"],
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=int(row["volume"]),
                    timeframe=1,  # 1min
                )
                try:
                    session.add(stock)
                    await session.flush()
                    inserted += 1
                except IntegrityError:
                    await session.rollback()
                    self.stats["skipped"] += 1
                    continue
            self.stats["inserted"] += inserted
            self.stats["total_records"] += len(df)
            print(f"  ✓ {symbol}: {inserted}/{len(df)} records")
            return inserted
        except Exception as e:
            print(f"  ✗ {symbol}: {e}")
            self.stats["errors"] += 1
            return 0

    async def run_week(self, week_start: datetime, week_end: datetime) -> None:
        """Load data for a single week across all symbols."""
        self.tracker["status"] = "loading"
        self._save_tracker()
        await self.load_symbols()
        async with AsyncSessionLocal() as session:
            # Create ETL log for this week
            job_id = f"weekly_load_{week_start.strftime('%Y%m%d')}_{week_end.strftime('%Y%m%d')}"
            etl_log = ETLLog(
                job_type="weekly_load",
                job_id=job_id,
                symbols=[s[0] for s in self.symbols],
                start_time=week_start,
                end_time=week_end,
                status="running",
                source="upstox",
                triggered_by="manual",
            )
            session.add(etl_log)
            await session.commit()

            for idx, (symbol, instrument_key) in enumerate(self.symbols, 1):
                print(f"[{idx}/{len(self.symbols)}] Processing {symbol} for {week_start.date()}–{week_end.date()}")
                await self.fetch_and_store(symbol, instrument_key, week_start, week_end, session)
                await session.commit()
                await asyncio.sleep(0.5)  # respect rate limits
                self.tracker["current_symbol_index"] = idx
                self._save_tracker()

            # Update ETL log
            etl_log.status = "success" if self.stats["errors"] == 0 else "partial"
            etl_log.records_fetched = self.stats["total_records"]
            etl_log.records_inserted = self.stats["inserted"]
            etl_log.records_skipped = self.stats["skipped"]
            await session.commit()

        # Week completed – update tracker
        self.tracker["last_start"] = week_start.isoformat()
        self.tracker["last_end"] = week_end.isoformat()
        self.tracker["status"] = "completed"
        self.tracker["current_symbol_index"] = 0
        self._save_tracker()
        print(f"Week {week_start.date()}–{week_end.date()} loaded successfully")

    async def run(self) -> None:
        """Iteratively load weeks starting from 2020‑11‑23 until today.
        The function can be stopped and resumed; it will continue from the last
        completed week recorded in the tracker file.
        """
        start_date = datetime(2020, 11, 23)
        # If a week was already completed, start from the next week
        if self.tracker["last_end"]:
            last_end = datetime.fromisoformat(self.tracker["last_end"]).date()
            start_date = datetime.combine(last_end + timedelta(days=1), datetime.min.time())
        today = datetime.now().date()
        while start_date.date() <= today:
            week_end = start_date + timedelta(days=6)
            if week_end.date() > today:
                week_end = datetime.combine(today, datetime.max.time())
            await self.run_week(start_date, week_end)
            # Move to next week
            start_date = week_end + timedelta(days=1)

if __name__ == "__main__":
    asyncio.run(WeeklyLoader().run())
