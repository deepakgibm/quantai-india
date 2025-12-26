"""
Upstox Historical Candle Data ETL Pipeline
===========================================

Production-grade ETL with:
- Checkpoint-based ingestion (restart-safe)
- Idempotent candle inserts (no duplicates)
- Incremental loading (only missing intervals)
- Rate limiting with exponential backoff
- Graceful partial failure handling
- Progress tracking and logging

Data Flow:
    Instrument Master → Candle Request Generator → Checkpoint Validator
    → Upstox Candle API → Deduplication Layer → Candle Storage → Checkpoint Update

Usage:
    python etl/upstox_candle_etl.py --interval day --resume
    python etl/upstox_candle_etl.py --interval 1minute --symbol RELIANCE
"""

import os
import sys
import json
import time
import argparse
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import requests
import psycopg2
from psycopg2.extras import execute_batch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.nifty500_instruments import NIFTY_500_MAPPING


# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """ETL Configuration"""
    
    # Database
    DB_HOST = "localhost"
    DB_PORT = 5432
    DB_USER = "postgres"
    DB_PASSWORD = "admin"
    DB_NAME = "quantai"
    
    # Upstox API
    UPSTOX_BASE_URL = "https://api.upstox.com/v2"
    UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN", "")
    
    # Rate Limiting
    REQUESTS_PER_MINUTE = 60  # Conservative limit
    RETRY_MAX_ATTEMPTS = 5
    RETRY_BASE_DELAY = 1.0  # seconds
    RETRY_MAX_DELAY = 60.0  # seconds
    
    # Date Range
    DEFAULT_START_DATE = "2022-01-03"
    DEFAULT_END_DATE = "2025-12-24"
    
    # Checkpoint
    CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), "checkpoints")
    
    # Intervals  
    INTERVAL_MAP = {
        "1minute": "1min",
        "5minute": "5min",
        "15minute": "15min",
        "30minute": "30min",
        "1day": "1d",
        "day": "1d"
    }


# =============================================================================
# LOGGING
# =============================================================================

def setup_logging(log_file: str = None) -> logging.Logger:
    """Configure logging with console and file handlers."""
    logger = logging.getLogger("upstox_etl")
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CandleData:
    """Single candle record."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    interval: str


@dataclass
class ETLCheckpoint:
    """Checkpoint for resume capability."""
    job_id: str
    interval: str
    start_date: str
    end_date: str
    total_symbols: int
    completed_symbols: List[str]
    failed_symbols: List[Dict[str, str]]
    current_symbol_index: int
    stats: Dict[str, int]
    started_at: str
    last_updated: str
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ETLCheckpoint':
        return cls(**data)


# =============================================================================
# RATE LIMITER
# =============================================================================

class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, requests_per_minute: int = 60):
        self.rate = requests_per_minute / 60.0  # requests per second
        self.tokens = requests_per_minute
        self.last_update = time.time()
        self.max_tokens = requests_per_minute
    
    def acquire(self):
        """Wait until a token is available."""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.rate)
        self.last_update = now
        
        if self.tokens < 1:
            wait_time = (1 - self.tokens) / self.rate
            time.sleep(wait_time)
            self.tokens = 0
        else:
            self.tokens -= 1


# =============================================================================
# UPSTOX API CLIENT
# =============================================================================

class UpstoxCandleClient:
    """Synchronous Upstox API client for historical candles."""
    
    def __init__(self, access_token: str, logger: logging.Logger):
        self.access_token = access_token
        self.base_url = Config.UPSTOX_BASE_URL
        self.logger = logger
        self.rate_limiter = RateLimiter(Config.REQUESTS_PER_MINUTE)
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        })
    
    def get_historical_candles(
        self,
        instrument_key: str,
        interval: str,
        from_date: date,
        to_date: date
    ) -> List[Dict]:
        """
        Fetch historical candles from Upstox API.
        
        Args:
            instrument_key: Upstox instrument key (e.g., "NSE_EQ|INE002A01018")
            interval: Candle interval (1minute, 5minute, 15minute, 30minute, day)
            from_date: Start date
            to_date: End date
            
        Returns:
            List of candle dictionaries
        """
        self.rate_limiter.acquire()
        
        # URL encode the instrument key
        encoded_key = requests.utils.quote(instrument_key, safe='')
        
        endpoint = f"{self.base_url}/historical-candle/{encoded_key}/{interval}/{to_date.isoformat()}/{from_date.isoformat()}"
        
        attempt = 0
        while attempt < Config.RETRY_MAX_ATTEMPTS:
            try:
                response = self.session.get(endpoint, timeout=30)
                
                if response.status_code == 429:
                    # Rate limited - exponential backoff
                    delay = min(
                        Config.RETRY_BASE_DELAY * (2 ** attempt),
                        Config.RETRY_MAX_DELAY
                    )
                    self.logger.warning(f"Rate limited. Waiting {delay:.1f}s...")
                    time.sleep(delay)
                    attempt += 1
                    continue
                
                if response.status_code == 401:
                    self.logger.error("Unauthorized - check access token")
                    return []
                
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") == "success" and data.get("data", {}).get("candles"):
                    return data["data"]["candles"]
                else:
                    return []
                    
            except requests.exceptions.Timeout:
                self.logger.warning(f"Request timeout (attempt {attempt + 1})")
                attempt += 1
                time.sleep(Config.RETRY_BASE_DELAY * (2 ** attempt))
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request error: {e} (attempt {attempt + 1})")
                attempt += 1
                if attempt < Config.RETRY_MAX_ATTEMPTS:
                    time.sleep(Config.RETRY_BASE_DELAY * (2 ** attempt))
                    
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                return []
        
        return []
    
    def close(self):
        """Close the session."""
        self.session.close()


# =============================================================================
# DATABASE MANAGER
# =============================================================================

class DatabaseManager:
    """PostgreSQL database manager with deduplication."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.conn = None
        self.connect()
    
    def connect(self):
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME
            )
            self.conn.autocommit = False
            self.logger.info("Connected to PostgreSQL database")
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            raise
    
    def get_existing_timestamps(
        self,
        symbol: str,
        interval: str,
        from_date: date,
        to_date: date
    ) -> set:
        """
        Get existing timestamps for a symbol/interval to avoid duplicates.
        
        Returns:
            Set of existing timestamps
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT timestamp FROM stock_data
                WHERE symbol = %s AND interval = %s
                AND timestamp >= %s AND timestamp <= %s
            """, (symbol, interval, from_date, to_date))
            
            existing = {row[0] for row in cursor.fetchall()}
            cursor.close()
            return existing
        except Exception as e:
            self.logger.error(f"Error fetching existing timestamps: {e}")
            return set()
    
    def get_last_timestamp(self, symbol: str, interval: str) -> Optional[datetime]:
        """Get the most recent timestamp for a symbol/interval."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT MAX(timestamp) FROM stock_data
                WHERE symbol = %s AND interval = %s
            """, (symbol, interval))
            
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result[0] else None
        except Exception as e:
            self.logger.error(f"Error fetching last timestamp: {e}")
            return None
    
    def insert_candles(self, candles: List[CandleData]) -> Tuple[int, int]:
        """
        Insert candles with duplicate handling.
        
        Returns:
            Tuple of (inserted_count, skipped_count)
        """
        if not candles:
            return 0, 0
        
        inserted = 0
        skipped = 0
        
        try:
            cursor = self.conn.cursor()
            
            for candle in candles:
                try:
                    cursor.execute("""
                        INSERT INTO stock_data (symbol, timestamp, open, high, low, close, volume, interval)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (symbol, timestamp, interval) DO NOTHING
                    """, (
                        candle.symbol,
                        candle.timestamp,
                        candle.open,
                        candle.high,
                        candle.low,
                        candle.close,
                        candle.volume,
                        candle.interval
                    ))
                    
                    if cursor.rowcount > 0:
                        inserted += 1
                    else:
                        skipped += 1
                except Exception as e:
                    skipped += 1
                    self.logger.debug(f"Insert error: {e}")
            
            self.conn.commit()
            cursor.close()
            return inserted, skipped
            
        except Exception as e:
            self.logger.error(f"Batch insert error: {e}")
            self.conn.rollback()
            return 0, len(candles)
    
    def get_symbol_count(self, interval: str) -> int:
        """Get count of distinct symbols for an interval."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT COUNT(DISTINCT symbol) FROM stock_data
                WHERE interval = %s
            """, (interval,))
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else 0
        except Exception as e:
            self.logger.error(f"Error counting symbols: {e}")
            return 0
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


# =============================================================================
# CHECKPOINT MANAGER
# =============================================================================

class CheckpointManager:
    """Manage ETL checkpoints for resume capability."""
    
    def __init__(self, interval: str, logger: logging.Logger):
        self.interval = interval
        self.logger = logger
        self.checkpoint_dir = Config.CHECKPOINT_DIR
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        self.checkpoint_file = os.path.join(
            self.checkpoint_dir, 
            f"upstox_etl_{interval}_checkpoint.json"
        )
    
    def load(self) -> Optional[ETLCheckpoint]:
        """Load existing checkpoint if available."""
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, 'r') as f:
                    data = json.load(f)
                    self.logger.info(f"Loaded checkpoint: {data['job_id']}")
                    return ETLCheckpoint.from_dict(data)
        except Exception as e:
            self.logger.warning(f"Could not load checkpoint: {e}")
        return None
    
    def save(self, checkpoint: ETLCheckpoint):
        """Save checkpoint to file."""
        try:
            checkpoint.last_updated = datetime.now().isoformat()
            with open(self.checkpoint_file, 'w') as f:
                json.dump(checkpoint.to_dict(), f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save checkpoint: {e}")
    
    def create_new(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str
    ) -> ETLCheckpoint:
        """Create a new checkpoint."""
        job_id = f"upstox_{self.interval}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return ETLCheckpoint(
            job_id=job_id,
            interval=self.interval,
            start_date=start_date,
            end_date=end_date,
            total_symbols=len(symbols),
            completed_symbols=[],
            failed_symbols=[],
            current_symbol_index=0,
            stats={
                "total_candles": 0,
                "inserted": 0,
                "skipped": 0,
                "errors": 0
            },
            started_at=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat()
        )
    
    def clear(self):
        """Remove checkpoint file."""
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
            self.logger.info("Checkpoint cleared")


# =============================================================================
# MAIN ETL PIPELINE
# =============================================================================

class UpstoxCandleETL:
    """
    Main ETL pipeline for Upstox historical candle data.
    
    Features:
    - Checkpoint-based resume
    - Incremental loading
    - Duplicate prevention
    - Rate limiting
    - Error handling
    """
    
    def __init__(
        self,
        interval: str = "day",
        start_date: str = None,
        end_date: str = None,
        resume: bool = True,
        symbols: List[str] = None,
        access_token: str = None
    ):
        self.interval = interval
        self.db_interval = Config.INTERVAL_MAP.get(interval, interval)
        self.start_date = start_date or Config.DEFAULT_START_DATE
        self.end_date = end_date or Config.DEFAULT_END_DATE
        self.resume = resume
        self.specific_symbols = symbols
        self.access_token = access_token or Config.UPSTOX_ACCESS_TOKEN
        
        # Initialize components
        self.logger = setup_logging()
        self.db = DatabaseManager(self.logger)
        self.checkpoint_mgr = CheckpointManager(interval, self.logger)
        self.api = UpstoxCandleClient(self.access_token, self.logger)
        
        # Get all symbols
        self.all_symbols = self._get_symbols()
    
    def _get_symbols(self) -> List[Tuple[str, str]]:
        """Get list of (symbol, instrument_key) tuples."""
        symbols = []
        
        if self.specific_symbols:
            for symbol in self.specific_symbols:
                if symbol in NIFTY_500_MAPPING:
                    symbols.append((symbol, NIFTY_500_MAPPING[symbol]))
                else:
                    self.logger.warning(f"Symbol {symbol} not found in instrument mapping")
        else:
            for symbol, instrument_key in NIFTY_500_MAPPING.items():
                symbols.append((symbol, instrument_key))
        
        return symbols
    
    def run(self) -> Dict[str, Any]:
        """
        Execute the ETL pipeline.
        
        Returns:
            Summary statistics
        """
        self.logger.info("=" * 60)
        self.logger.info("UPSTOX CANDLE ETL PIPELINE")
        self.logger.info("=" * 60)
        self.logger.info(f"Interval: {self.interval} (stored as: {self.db_interval})")
        self.logger.info(f"Date Range: {self.start_date} to {self.end_date}")
        self.logger.info(f"Total Symbols: {len(self.all_symbols)}")
        
        # Load or create checkpoint
        checkpoint = None
        if self.resume:
            checkpoint = self.checkpoint_mgr.load()
        
        if checkpoint:
            self.logger.info(f"Resuming from checkpoint: {checkpoint.job_id}")
            self.logger.info(f"Completed: {len(checkpoint.completed_symbols)}/{checkpoint.total_symbols}")
            start_index = checkpoint.current_symbol_index
        else:
            symbol_names = [s[0] for s in self.all_symbols]
            checkpoint = self.checkpoint_mgr.create_new(
                symbol_names,
                self.start_date,
                self.end_date
            )
            start_index = 0
            self.logger.info(f"Starting new ETL job: {checkpoint.job_id}")
        
        # Parse date range
        from_date = datetime.strptime(self.start_date, "%Y-%m-%d").date()
        to_date = datetime.strptime(self.end_date, "%Y-%m-%d").date()
        
        # Process symbols
        try:
            for i, (symbol, instrument_key) in enumerate(self.all_symbols[start_index:], start=start_index):
                progress = f"[{i+1}/{len(self.all_symbols)}]"
                self.logger.info(f"{progress} Processing {symbol}...")
                
                # Update checkpoint
                checkpoint.current_symbol_index = i
                
                try:
                    # Check for incremental loading
                    last_ts = self.db.get_last_timestamp(symbol, self.db_interval)
                    if last_ts:
                        # Adjust from_date to load only new data
                        actual_from = (last_ts.date() + timedelta(days=1))
                        if actual_from >= to_date:
                            self.logger.info(f"  ⚠ Already up to date, skipping")
                            checkpoint.completed_symbols.append(symbol)
                            checkpoint.stats["skipped"] += 1
                            continue
                        effective_from = actual_from
                    else:
                        effective_from = from_date
                    
                    # Fetch candles from API
                    raw_candles = self.api.get_historical_candles(
                        instrument_key,
                        self.interval,
                        effective_from,
                        to_date
                    )
                    
                    if not raw_candles:
                        self.logger.warning(f"  ✗ No data available")
                        checkpoint.failed_symbols.append({
                            "symbol": symbol,
                            "error": "No data available"
                        })
                        checkpoint.stats["errors"] += 1
                        continue
                    
                    # Parse candles
                    candles = []
                    for c in raw_candles:
                        try:
                            candles.append(CandleData(
                                symbol=symbol,
                                timestamp=datetime.fromisoformat(c[0].replace('Z', '+00:00')),
                                open=float(c[1]),
                                high=float(c[2]),
                                low=float(c[3]),
                                close=float(c[4]),
                                volume=int(c[5]),
                                interval=self.db_interval
                            ))
                        except Exception as e:
                            self.logger.debug(f"Parse error: {e}")
                    
                    # Insert to database
                    inserted, skipped = self.db.insert_candles(candles)
                    
                    checkpoint.stats["total_candles"] += len(candles)
                    checkpoint.stats["inserted"] += inserted
                    checkpoint.stats["skipped"] += skipped
                    checkpoint.completed_symbols.append(symbol)
                    
                    self.logger.info(f"  ✓ Loaded {inserted} candles (skipped {skipped} duplicates)")
                    
                except Exception as e:
                    self.logger.error(f"  ✗ Error: {e}")
                    checkpoint.failed_symbols.append({
                        "symbol": symbol,
                        "error": str(e)
                    })
                    checkpoint.stats["errors"] += 1
                
                # Save checkpoint periodically
                if (i + 1) % 10 == 0:
                    self.checkpoint_mgr.save(checkpoint)
            
            # Final checkpoint save
            checkpoint.current_symbol_index = len(self.all_symbols)
            self.checkpoint_mgr.save(checkpoint)
            
        except KeyboardInterrupt:
            self.logger.warning("ETL interrupted by user")
            self.checkpoint_mgr.save(checkpoint)
            self.logger.info("Progress saved to checkpoint. Resume with --resume flag.")
        
        finally:
            self.api.close()
            self.db.close()
        
        # Print summary
        self._print_summary(checkpoint)
        
        return checkpoint.stats
    
    def _print_summary(self, checkpoint: ETLCheckpoint):
        """Print ETL summary."""
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("ETL SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Job ID: {checkpoint.job_id}")
        self.logger.info(f"Interval: {checkpoint.interval}")
        self.logger.info(f"Completed: {len(checkpoint.completed_symbols)}/{checkpoint.total_symbols}")
        self.logger.info(f"Failed: {len(checkpoint.failed_symbols)}")
        self.logger.info(f"Total Candles: {checkpoint.stats['total_candles']}")
        self.logger.info(f"Inserted: {checkpoint.stats['inserted']}")
        self.logger.info(f"Skipped (duplicates): {checkpoint.stats['skipped']}")
        self.logger.info(f"Errors: {checkpoint.stats['errors']}")
        
        # Current DB state
        symbol_count = self.db.get_symbol_count(self.db_interval)
        self.logger.info(f"Symbols in DB ({self.db_interval}): {symbol_count}")
        
        if checkpoint.failed_symbols:
            self.logger.info("")
            self.logger.info("Failed Symbols:")
            for fs in checkpoint.failed_symbols[:10]:
                self.logger.info(f"  - {fs['symbol']}: {fs['error']}")
            if len(checkpoint.failed_symbols) > 10:
                self.logger.info(f"  ... and {len(checkpoint.failed_symbols) - 10} more")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Upstox Historical Candle ETL Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python upstox_candle_etl.py --interval day
  python upstox_candle_etl.py --interval day --resume
  python upstox_candle_etl.py --interval 1minute --symbol RELIANCE TCS
  python upstox_candle_etl.py --interval 5minute --start-date 2024-01-01
        """
    )
    
    parser.add_argument(
        "--interval",
        choices=["1minute", "5minute", "15minute", "30minute", "day"],
        default="day",
        help="Candle interval (default: day)"
    )
    parser.add_argument(
        "--start-date",
        default=Config.DEFAULT_START_DATE,
        help=f"Start date YYYY-MM-DD (default: {Config.DEFAULT_START_DATE})"
    )
    parser.add_argument(
        "--end-date",
        default=Config.DEFAULT_END_DATE,
        help=f"End date YYYY-MM-DD (default: {Config.DEFAULT_END_DATE})"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint"
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Start fresh (ignore checkpoint)"
    )
    parser.add_argument(
        "--symbol",
        nargs="+",
        help="Specific symbol(s) to process"
    )
    parser.add_argument(
        "--token",
        help="Upstox access token (or set UPSTOX_ACCESS_TOKEN env var)"
    )
    
    args = parser.parse_args()
    
    # Load token from .env if not provided
    if not args.token:
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("UPSTOX_ACCESS_TOKEN="):
                        args.token = line.split("=", 1)[1].strip()
                        break
    
    if not args.token:
        print("ERROR: Upstox access token required. Set UPSTOX_ACCESS_TOKEN or use --token")
        sys.exit(1)
    
    # Create and run ETL
    etl = UpstoxCandleETL(
        interval=args.interval,
        start_date=args.start_date,
        end_date=args.end_date,
        resume=args.resume and not args.fresh,
        symbols=args.symbol,
        access_token=args.token
    )
    
    if args.fresh:
        etl.checkpoint_mgr.clear()
    
    etl.run()


if __name__ == "__main__":
    main()
