"""
Intraday Candles Model and Data Loader for Nifty 500
Fetches 1-minute and 30-minute data from Upstox, resamples to 3/5/15 min locally.
Includes CHECKPOINT/RESUME functionality for fault tolerance.

UPSTOX SUPPORTED INTERVALS: 1minute, 30minute, day, week, month
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict
import pandas as pd
import asyncio

from sqlalchemy import Column, String, Float, Integer, DateTime, Index, create_engine, func
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()


class IntradayCandle(Base):
    """Intraday candle data for Nifty 500 stocks."""
    __tablename__ = "intraday_candles"
    
    symbol = Column(String(50), primary_key=True)
    timestamp = Column(DateTime, primary_key=True)
    interval = Column(String(10), primary_key=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    source = Column(String(20), default="upstox")


class LoaderCheckpoint(Base):
    """Checkpoint table for tracking progress."""
    __tablename__ = "loader_checkpoints"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), nullable=False, index=True)
    symbol = Column(String(50), nullable=False)
    status = Column(String(20), default="pending")
    last_date_loaded = Column(DateTime)
    records_inserted = Column(Integer, default=0)
    error_message = Column(String(500))
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (
        Index('idx_job_symbol', 'job_id', 'symbol', unique=True),
    )


class IntradayDataLoader:
    """
    Loads intraday data from Upstox API for Nifty 500 stocks.
    
    Strategy:
    - Fetch 1-minute data from Upstox
    - Resample locally to 3m, 5m, 15m
    - Fetch 30-minute data directly from Upstox
    """
    
    CHECKPOINT_FILE = "loader_checkpoint.json"
    
    def __init__(self):
        from config import settings
        from services.upstox_client import get_upstox_client
        
        self.client = get_upstox_client()
        
        self._engine = create_engine(settings.SYNC_DATABASE_URL)
        self._Session = sessionmaker(bind=self._engine)
        
        Base.metadata.create_all(self._engine)
        
        self.stats = {
            "symbols_processed": 0,
            "records_inserted": 0,
            "errors": 0,
            "resumed": False
        }
    
    def resample_ohlcv(self, df_1m: pd.DataFrame, minutes: int) -> pd.DataFrame:
        """Resample 1-minute OHLCV data to larger interval."""
        if df_1m.empty:
            return pd.DataFrame()
        
        df = df_1m.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
        
        resampled = df.resample(f'{minutes}min', label='left', closed='left').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        resampled = resampled.reset_index()
        return resampled
    
    def get_nifty500_symbols(self) -> List[Tuple[str, str]]:
        """Get Nifty 500 symbols from database."""
        from services.nifty500_fetcher import Nifty500Symbol
        
        session = self._Session()
        try:
            symbols = session.query(Nifty500Symbol).all()
            return [(s.symbol, s.instrument_key) for s in symbols]
        finally:
            session.close()
    
    def get_last_loaded_date(self, symbol: str) -> Optional[datetime]:
        """Get last loaded date for a symbol."""
        session = self._Session()
        try:
            result = session.query(func.max(IntradayCandle.timestamp)).filter(
                IntradayCandle.symbol == symbol,
                IntradayCandle.interval == "1m"
            ).scalar()
            return result
        finally:
            session.close()
    
    def save_checkpoint(self, data: Dict):
        """Save checkpoint to JSON file."""
        data["saved_at"] = datetime.now().isoformat()
        path = os.path.join(os.path.dirname(__file__), "..", self.CHECKPOINT_FILE)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"  [Checkpoint saved: {data.get('current_index', 0)}/{data.get('total', 0)}]")
    
    def load_checkpoint(self) -> Optional[Dict]:
        """Load checkpoint from JSON file."""
        path = os.path.join(os.path.dirname(__file__), "..", self.CHECKPOINT_FILE)
        if os.path.exists(path):
            try:
                with open(path) as f:
                    return json.load(f)
            except:
                pass
        return None
    
    def clear_checkpoint(self):
        """Clear checkpoint file."""
        path = os.path.join(os.path.dirname(__file__), "..", self.CHECKPOINT_FILE)
        if os.path.exists(path):
            os.remove(path)
    
    def store_candles(self, symbol: str, df: pd.DataFrame, interval: str) -> int:
        """Store candles to database."""
        if df.empty:
            return 0
        
        session = self._Session()
        try:
            inserted = 0
            for _, row in df.iterrows():
                try:
                    candle = IntradayCandle(
                        symbol=symbol,
                        timestamp=row['timestamp'],
                        interval=interval,
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=float(row['close']),
                        volume=int(row['volume']),
                        source="upstox"
                    )
                    session.merge(candle)
                    inserted += 1
                except:
                    pass
            session.commit()
            return inserted
        finally:
            session.close()
    
    async def fetch_symbol_data(
        self,
        symbol: str,
        instrument_key: str,
        from_date: datetime,
        to_date: datetime
    ) -> int:
        """Fetch all interval data for a single symbol."""
        total_inserted = 0
        
        # Check for existing data - resume
        last_loaded = self.get_last_loaded_date(symbol)
        if last_loaded and last_loaded > from_date:
            from_date = last_loaded + timedelta(minutes=1)
            print(f"    Resuming from {from_date.date()}")
        
        if from_date >= to_date:
            print(f"    Already up to date")
            return 0
        
        # Fetch in chunks (max 15 days for intraday)
        chunk_size = timedelta(days=7)
        current_from = from_date
        
        all_1m_data = []
        all_30m_data = []
        
        while current_from < to_date:
            current_to = min(current_from + chunk_size, to_date)
            
            try:
                # Fetch 1-minute data
                df_1m = await self.client.get_historical_data(
                    symbol=symbol,
                    instrument_key=instrument_key,
                    from_date=current_from,
                    to_date=current_to,
                    interval="1minute"
                )
                if not df_1m.empty:
                    all_1m_data.append(df_1m)
                
                # Fetch 30-minute data
                df_30m = await self.client.get_historical_data(
                    symbol=symbol,
                    instrument_key=instrument_key,
                    from_date=current_from,
                    to_date=current_to,
                    interval="30minute"
                )
                if not df_30m.empty:
                    all_30m_data.append(df_30m)
                
                await asyncio.sleep(0.3)  # Rate limiting
                
            except Exception as e:
                error_msg = str(e)
                if "rate" in error_msg.lower() or "limit" in error_msg.lower():
                    print(f"    Rate limited - waiting 30s...")
                    await asyncio.sleep(30)
                else:
                    self.stats["errors"] += 1
            
            current_from = current_to
        
        # Combine and store data
        if all_1m_data:
            df_1m_combined = pd.concat(all_1m_data, ignore_index=True).drop_duplicates(subset=['timestamp'])
            
            # Store 1-minute data
            count = self.store_candles(symbol, df_1m_combined, "1m")
            total_inserted += count
            print(f"    1m: {count} records")
            
            # Resample and store 3m, 5m, 15m
            for interval_name, minutes in [("3m", 3), ("5m", 5), ("15m", 15)]:
                df_resampled = self.resample_ohlcv(df_1m_combined, minutes)
                count = self.store_candles(symbol, df_resampled, interval_name)
                total_inserted += count
                print(f"    {interval_name}: {count} records")
        
        # Store 30-minute data
        if all_30m_data:
            df_30m_combined = pd.concat(all_30m_data, ignore_index=True).drop_duplicates(subset=['timestamp'])
            count = self.store_candles(symbol, df_30m_combined, "30m")
            total_inserted += count
            print(f"    30m: {count} records")
        
        return total_inserted
    
    async def load_full_dataset(self, years: int = 3, resume: bool = True) -> dict:
        """
        Load intraday data for all Nifty 500 stocks.
        
        Args:
            years: Number of years of historical data
            resume: Whether to resume from last checkpoint
        """
        start_time = datetime.now()
        
        print("=" * 70)
        print("NIFTY 500 INTRADAY DATA LOADER")
        print("=" * 70)
        
        to_date = datetime.now()
        from_date = to_date - timedelta(days=years * 365)
        # Use a stable job ID based on duration, not the exact current timestamp
        job_id = f"load_{years}y_nifty500"
        
        print(f"Date range: {from_date.date()} to {to_date.date()} ({years} years)")
        print(f"Intervals: 1m, 3m, 5m, 15m, 30m")
        print(f"Job ID: {job_id}")
        
        symbols = self.get_nifty500_symbols()
        print(f"Total symbols: {len(symbols)}")
        
        # Check for checkpoint
        start_index = 0
        if resume:
            checkpoint = self.load_checkpoint()
            # Allow resuming if the job_id matches or if it's any 'load_' job
            if checkpoint and (checkpoint.get("job_id") == job_id or checkpoint.get("job_id", "").startswith("load_")):
                start_index = checkpoint.get("current_index", 0)
                self.stats = checkpoint.get("stats", self.stats)
                self.stats["resumed"] = True
                print(f"RESUMING from symbol #{start_index} (Previous Job ID: {checkpoint.get('job_id')})")
        
        print()
        
        # Process each symbol
        for i, (symbol, instrument_key) in enumerate(symbols[start_index:], start_index + 1):
            print(f"[{i}/{len(symbols)}] {symbol}")
            
            try:
                count = await self.fetch_symbol_data(symbol, instrument_key, from_date, to_date)
                self.stats["records_inserted"] += count
                self.stats["symbols_processed"] += 1
            except Exception as e:
                print(f"  ERROR: {e}")
                self.stats["errors"] += 1
            
            # Save checkpoint every 10 symbols
            if i % 10 == 0:
                self.save_checkpoint({
                    "job_id": job_id,
                    "current_index": i,
                    "total": len(symbols),
                    "stats": self.stats
                })
                
                elapsed = (datetime.now() - start_time).total_seconds()
                done = i - start_index
                rate = done / elapsed * 60 if elapsed > 0 else 0
                eta = (len(symbols) - i) / rate if rate > 0 else 0
                print(f"\nProgress: {i}/{len(symbols)} ({i/len(symbols)*100:.1f}%)")
                print(f"Elapsed: {elapsed/60:.1f} min | ETA: {eta:.1f} min")
                print(f"Records: {self.stats['records_inserted']:,} | Errors: {self.stats['errors']}\n")
        
        # Clear checkpoint on completion
        self.clear_checkpoint()
        
        duration = (datetime.now() - start_time).total_seconds()
        print("\n" + "=" * 70)
        print("LOAD COMPLETE")
        print("=" * 70)
        print(f"Symbols: {self.stats['symbols_processed']}")
        print(f"Records: {self.stats['records_inserted']:,}")
        print(f"Errors: {self.stats['errors']}")
        print(f"Duration: {duration/60:.1f} minutes")
        
        return self.stats
    
    def get_candles(self, symbol: str, interval: str, limit: int = 100) -> pd.DataFrame:
        """Get intraday candles from database."""
        from sqlalchemy import desc
        
        session = self._Session()
        try:
            candles = session.query(IntradayCandle).filter(
                IntradayCandle.symbol == symbol,
                IntradayCandle.interval == interval
            ).order_by(desc(IntradayCandle.timestamp)).limit(limit).all()
            
            if not candles:
                return pd.DataFrame()
            
            data = [{
                'timestamp': c.timestamp, 'open': c.open, 'high': c.high,
                'low': c.low, 'close': c.close, 'volume': c.volume
            } for c in reversed(candles)]
            
            return pd.DataFrame(data).set_index('timestamp')
        finally:
            session.close()


# CLI interface
if __name__ == "__main__":
    import sys
    
    loader = IntradayDataLoader()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "load":
            years = int(sys.argv[2]) if len(sys.argv) > 2 else 3
            resume = "--no-resume" not in sys.argv
            asyncio.run(loader.load_full_dataset(years=years, resume=resume))
        
        elif cmd == "clear":
            loader.clear_checkpoint()
            print("Checkpoint cleared")
        
        else:
            print(f"Unknown command: {cmd}")
    else:
        print("Usage:")
        print("  python intraday_loader.py load [years] [--no-resume]")
        print("  python intraday_loader.py clear")
