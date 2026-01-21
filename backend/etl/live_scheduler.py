"""
Live Data Scheduler for AlphaPrime Module

APScheduler-based job that:
- Fetches live market data every 5 minutes
- Updates the database
- Triggers signal generation
"""

import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.exc import IntegrityError

from database import AsyncSessionLocal
from models_alpha import StockCandle, ETLLog
from services.upstox_client import get_upstox_client
from services.instrument_resolver import resolve_instrument_id
from config import settings


class LiveDataScheduler:
    """5-minute interval live data fetcher"""
    
    def __init__(self):
        self.client = get_upstox_client()
        self.scheduler = AsyncIOScheduler()
        self.symbols = []
        self.is_running = False
    
    async def fetch_live_data(self):
        """Fetch current market data for all symbols"""
        job_start = datetime.now()
        stats = {"inserted": 0, "skipped": 0, "errors": 0}
        
        print(f"\n[{job_start.strftime('%H:%M:%S')}] Live Data Fetch Started")
        
        # Load symbols if not already loaded
        if not self.symbols:
            self.symbols = await self.client.get_nifty_200_symbols()
        
        async with AsyncSessionLocal() as session:
            # Create ETL log
            etl_log = ETLLog(
                job_type="live_ingest",
                job_id=f"live_{job_start.strftime('%Y%m%d_%H%M%S')}",
                symbols=[s[0] for s in self.symbols],
                status="running",
                source="upstox",
                triggered_by="scheduler"
            )
            session.add(etl_log)
            await session.commit()
            
            # Fetch quotes for each symbol
            for symbol, instrument_key in self.symbols:
                try:
                    quote = await self.client.get_live_quote(instrument_key, symbol)
                    
                    if quote is None:
                        stats["errors"] += 1
                        continue


                    
                    # Resolve symbol to instrument_id
                    instrument_id = resolve_instrument_id(symbol)
                    if not instrument_id:
                        stats["errors"] += 1
                        continue
                        
                    # Create stock candle record
                    stock_data = StockCandle(
                        instrument_id=instrument_id,
                        candle_ts=quote["timestamp"],
                        open=float(quote["open"]),
                        high=float(quote["high"]),
                        low=float(quote["low"]),
                        close=float(quote["close"] or quote["last_price"]),
                        volume=int(quote["volume"]),
                        timeframe=5,  # 5min
                    )
                    
                    try:
                        session.add(stock_data)
                        await session.flush()
                        stats["inserted"] += 1
                    except IntegrityError:
                        await session.rollback()
                        stats["skipped"] += 1
                
                except Exception as e:
                    print(f"  Error fetching {symbol}: {e}")
                    stats["errors"] += 1
            
            # Commit all records
            await session.commit()
            
            # Update ETL log
            duration = (datetime.now() - job_start).total_seconds()
            etl_log.status = "success" if stats["errors"] == 0 else "partial"
            etl_log.records_inserted = stats["inserted"]
            etl_log.records_skipped = stats["skipped"]
            etl_log.duration_seconds = duration
            
            await session.commit()
        
        print(f"  ✓ Inserted: {stats['inserted']}, Skipped: {stats['skipped']}, Errors: {stats['errors']}")
        print(f"  Duration: {duration:.2f}s\n")
    
    def start(self):
        """Start the scheduler"""
        if self.is_running:
            print("Scheduler is already running")
            return
        
        # Add job with interval trigger
        self.scheduler.add_job(
            self.fetch_live_data,
            trigger=IntervalTrigger(minutes=settings.LIVE_DATA_INTERVAL_MINUTES),
            id="live_data_fetch",
            name="Live Market Data Fetcher",
            replace_existing=True
        )
        
        self.scheduler.start()
        self.is_running = True
        
        print(f"\n{'='*60}")
        print("Live Data Scheduler Started")
        print(f"Interval: Every {settings.LIVE_DATA_INTERVAL_MINUTES} minutes")
        print(f"{'='*60}\n")
    
    def stop(self):
        """Stop the scheduler"""
        if not self.is_running:
            return
        
        self.scheduler.shutdown()
        self.is_running = False
        print("\nScheduler stopped")


# Singleton instance
_scheduler = None

def get_scheduler() -> LiveDataScheduler:
    """Get or create singleton scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = LiveDataScheduler()
    return _scheduler


async def main():
    """CLI entry point for testing"""
    scheduler = get_scheduler()
    scheduler.start()
    
    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
