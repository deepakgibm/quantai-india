"""
Multi-Interval Nifty 200 Data Loader
Loads data for all Nifty 200 stocks with multiple timeframes from Upstox API
Intervals: 1min, 3min, 5min, 15min, 30min
Period: January 2022 to Today
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple
from sqlalchemy.exc import IntegrityError

# Add project root
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from backend.database import AsyncSessionLocal, init_db
from backend.models_alpha import StockData, ETLLog
from backend.services.upstox_client import get_upstox_client

class MultiIntervalLoader:
    """Load multiple intervals for Nifty 200 stocks"""
    
    # All intervals to load
    INTERVALS = ["1minute", "3minute", "5minute", "15minute", "30minute"]
    
    def __init__(self):
        self.client = get_upstox_client()
        self.stats = {
            "total_symbols": 0,
            "total_intervals": len(self.INTERVALS),
            "records_inserted": 0,
            "records_skipped": 0,
            "errors": 0,
            "start_time": datetime.now()
        }
    
    async def get_nifty200_symbols(self) -> List[Tuple[str, str]]:
        """
        Get Nifty 200 symbol to instrument key mapping
        Currently using available mapping (19 symbols)
        TODO: Fetch full 200 from Upstox instruments API
        """
        symbols = await self.client.get_nifty_200_symbols()
        print(f"   Loaded {len(symbols)} symbols")
        print(f"   (Note: Full Nifty 200 = 200 symbols, need to expand mapping)")
        return symbols
    
    async def load_interval_data(
        self,
        symbol: str,
        instrument_key: str,
        interval: str,
        from_date: datetime,
        to_date: datetime,
        session
    ) -> int:
        """Load data for one symbol, one interval"""
        try:
            print(f"      Fetching {interval} data...", end=" ")
            
            df = await self.client.get_historical_data(
                symbol=symbol,
                instrument_key=instrument_key,
                from_date=from_date,
                to_date=to_date,
                interval=interval
            )
            
            if df.empty:
                print("No data")
                return 0
            
            # Convert interval to short form for database
            interval_short = interval.replace("minute", "min")
            
            inserted = 0
            for _, row in df.iterrows():
                record = StockData(
                    symbol=row['symbol'],
                    timestamp=row['timestamp'],
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume'],
                    interval=interval_short,
                    source="upstox"
                )
                try:
                    session.add(record)
                    await session.flush()
                    inserted += 1
                except IntegrityError:
                    await session.rollback()
                    self.stats["records_skipped"] += 1
            
            await session.commit()
            self.stats["records_inserted"] += inserted
            print(f"✓ {inserted:,} records")
            return inserted
            
        except Exception as e:
            print(f"✗ Error: {e}")
            self.stats["errors"] += 1
            await session.rollback()
            return 0
    
    async def load_symbol_all_intervals(
        self,
        symbol: str,
        instrument_key: str,
        from_date: datetime,
        to_date: datetime,
        session
    ) -> dict:
        """Load all intervals for one symbol"""
        results = {}
        
        # Load each interval sequentially
        for interval in self.INTERVALS:
            count = await self.load_interval_data(
                symbol, instrument_key, interval,
                from_date, to_date, session
            )
            results[interval] = count
            
            # Small delay between intervals
            await asyncio.sleep(0.3)
        
        return results
    
    async def run(self):
        """Main execution"""
        print("\n" + "="*80)
        print("NIFTY 200 MULTI-INTERVAL DATA LOADER")
        print("="*80)
        print()
        print(f"📅 Period: January 1, 2022 → Today")
        print(f"⏱️  Intervals: {', '.join(self.INTERVALS)}")
        print()
        
        # Initialize database
        await init_db()
        
        # Date range
        from_date = datetime(2022, 1, 1)  # Jan 1, 2022
        to_date = datetime.now()
        days = (to_date - from_date).days
        
        print(f"📊 Date Range Details:")
        print(f"   Start: {from_date.strftime('%Y-%m-%d')}")
        print(f"   End: {to_date.strftime('%Y-%m-%d')}")
        print(f"   Duration: {days} days (~{days/365:.1f} years)")
        print()
        
        # Get symbols
        print("🔍 Fetching Nifty 200 symbols...")
        symbols = await self.get_nifty200_symbols()
        self.stats["total_symbols"] = len(symbols)
        print()
        
        # Estimate
        print("📈 Estimated Data Points:")
        trading_days = days * (252/365)  # Approx trading days
        minutes_per_day = 375  # 9:15 AM to 3:30 PM
        
        for interval in self.INTERVALS:
            interval_mins = int(interval.replace("minute", ""))
            candles_per_symbol = (trading_days * minutes_per_day / interval_mins)
            total_candles = candles_per_symbol * len(symbols)
            print(f"   {interval:10s}: ~{total_candles:,.0f} candles ({candles_per_symbol:,.0f} per symbol)")
        print()
        
        # Confirmation
        total_estimate = trading_days * minutes_per_day * len(symbols) * len(self.INTERVALS)
        print(f"⚠️  TOTAL ESTIMATED RECORDS: ~{total_estimate:,.0f}")
        print(f"⚠️  ESTIMATED TIME: ~{len(symbols) * len(self.INTERVALS) * 2 / 60:.1f} hours")
        print(f"⚠️  This will make {len(symbols) * len(self.INTERVALS)} API calls to Upstox")
        print()
        
        # Start loading
        async with AsyncSessionLocal() as session:
            # Create ETL log
            etl_log = ETLLog(
                job_type="nifty200_multi_interval_load",
                status="running",
                start_time=self.stats["start_time"],
                source="upstox"
            )
            session.add(etl_log)
            await session.commit()
            
            print("🚀 Starting data load...")
            print("="*80)
            print()
            
            for idx, (symbol, instrument_key) in enumerate(symbols, 1):
                print(f"[{idx}/{len(symbols)}] {symbol}")
                
                results = await self.load_symbol_all_intervals(
                    symbol, instrument_key,
                    from_date, to_date,
                    session
                )
                
                # Summary for this symbol
                total_for_symbol = sum(results.values())
                print(f"   └─ Total: {total_for_symbol:,} records across {len(self.INTERVALS)} intervals")
                print()
                
                # Rate limiting delay
                await asyncio.sleep(1)
            
            # Update ETL log
            duration = (datetime.now() - self.stats["start_time"]).total_seconds()
            etl_log.status = "success" if self.stats["errors"] == 0 else "partial"
            etl_log.end_time = datetime.now()
            etl_log.records_inserted = self.stats["records_inserted"]
            etl_log.duration_seconds = duration
            await session.commit()
        
        # Final summary
        print("="*80)
        print("LOAD COMPLETE")
        print("="*80)
        print(f"✅ Symbols Processed: {self.stats['total_symbols']}")
        print(f"✅ Intervals Loaded: {', '.join(self.INTERVALS)}")
        print(f"✅ Records Inserted: {self.stats['records_inserted']:,}")
        print(f"⏭️  Records Skipped: {self.stats['records_skipped']:,}")
        print(f"❌ Errors: {self.stats['errors']}")
        print(f"⏱️  Duration: {duration/60:.1f} minutes")
        print(f"⚡ Speed: {self.stats['records_inserted']/duration:.0f} records/second")
        print("="*80)


async def main():
    """Entry point"""
    loader = MultiIntervalLoader()
    await loader.run()


if __name__ == "__main__":
    print("\n⚠️  WARNING: This will load a large amount of data!")
    print("⚠️  Make sure you have:")
    print("   1. Valid Upstox API credentials in .env")
    print("   2. Sufficient disk space (~2-3 GB)")
    print("   3. Stable internet connection")
    print("   4. Time (this may take 1-2 hours)")
    print()
    
    response = input("Do you want to proceed? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        asyncio.run(main())
    else:
        print("Load cancelled.")
