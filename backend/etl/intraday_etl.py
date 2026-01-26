"""
Multi-Source Intraday ETL Pipeline
===================================

Loads intraday data from multiple sources:
- Upstox API: 1minute, 30minute intervals (recent data only ~30 days)
- yfinance: 5minute, 15minute intervals (up to 60 days)

For longer historical data (2022+), daily data from Upstox is the only reliable source.
Intraday data is typically limited to recent periods due to exchange/API limitations.

Usage:
    python etl/intraday_etl.py --interval 5m --source yfinance
    python etl/intraday_etl.py --interval 1m --source upstox
    python etl/intraday_etl.py --all-intraday
"""

import os
import sys
import json
import time
import argparse
import logging
from datetime import datetime, timedelta
from typing import Tuple
import requests
import psycopg2
import yfinance as yf
import pandas as pd
from urllib.parse import quote

# Add parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.nifty500_instruments import NIFTY_500_MAPPING


# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    DB_HOST = "localhost"
    DB_PORT = 5432
    DB_USER = "postgres"
    DB_PASSWORD = "admin"
    DB_NAME = "quantai"
    
    UPSTOX_BASE_URL = "https://api.upstox.com/v2"
    CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), "checkpoints")
    
    # API rate limits
    UPSTOX_RPM = 60
    YFINANCE_DELAY = 0.5
    
    # Intraday limitations
    YFINANCE_MAX_DAYS = {
        "1m": 7,      # Only 7 days for 1m
        "5m": 60,     # 60 days for 5m
        "15m": 60,    # 60 days for 15m
        "30m": 60,    # 60 days for 30m
    }
    
    UPSTOX_MAX_DAYS = {
        "1minute": 30,
        "30minute": 30,
    }
    
    # Interval mapping to DB format
    INTERVAL_MAP = {
        "1m": "1min",
        "1minute": "1min",
        "5m": "5min",
        "5minute": "5min",
        "15m": "15min",
        "15minute": "15min",
        "30m": "30min",
        "30minute": "30min",
    }


def setup_logging():
    logger = logging.getLogger("intraday_etl")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%H:%M:%S')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


# =============================================================================
# DATABASE
# =============================================================================

class Database:
    def __init__(self, logger):
        self.logger = logger
        self.conn = psycopg2.connect(
            host=Config.DB_HOST, port=Config.DB_PORT,
            user=Config.DB_USER, password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        self.conn.autocommit = False
    
    def insert_candles(self, df: pd.DataFrame, symbol: str, db_interval: str) -> Tuple[int, int]:
        if df.empty:
            return 0, 0
        
        inserted = 0
        skipped = 0
        cursor = self.conn.cursor()
        
        for _, row in df.iterrows():
            try:
                cursor.execute("""
                    INSERT INTO stock_data (symbol, timestamp, open, high, low, close, volume, interval)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol, timestamp, interval) DO NOTHING
                """, (
                    symbol,
                    row['timestamp'],
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    int(row['volume']),
                    db_interval
                ))
                if cursor.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as e:
                skipped += 1
        
        self.conn.commit()
        cursor.close()
        return inserted, skipped
    
    def get_symbol_count(self, interval: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT symbol) FROM stock_data WHERE interval = %s", (interval,))
        result = cursor.fetchone()
        cursor.close()
        return result[0] if result else 0
    
    def close(self):
        self.conn.close()


# =============================================================================
# YFINANCE LOADER
# =============================================================================

class YFinanceLoader:
    def __init__(self, logger):
        self.logger = logger
    
    def load_symbol(self, symbol: str, interval: str, days_back: int = 60) -> pd.DataFrame:
        """Load intraday data from yfinance."""
        ticker = f"{symbol}.NS"
        yf_interval = interval  # 5m, 15m, 30m
        
        max_days = Config.YFINANCE_MAX_DAYS.get(interval, 60)
        days_back = min(days_back, max_days)
        
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=f"{days_back}d", interval=yf_interval)
            
            if df.empty:
                # Try BSE
                ticker = f"{symbol}.BO"
                stock = yf.Ticker(ticker)
                df = stock.history(period=f"{days_back}d", interval=yf_interval)
            
            if df.empty:
                return pd.DataFrame()
            
            df = df.reset_index()
            df.columns = [c.lower() for c in df.columns]
            df = df.rename(columns={'datetime': 'timestamp', 'date': 'timestamp'})
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Ensure timezone-naive
            if df['timestamp'].dt.tz is not None:
                df['timestamp'] = df['timestamp'].dt.tz_localize(None)
            
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            self.logger.debug(f"yfinance error for {symbol}: {e}")
            return pd.DataFrame()


# =============================================================================
# UPSTOX LOADER
# =============================================================================

class UpstoxLoader:
    def __init__(self, token: str, logger):
        self.token = token
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        })
        self.last_request = 0
    
    def _rate_limit(self):
        elapsed = time.time() - self.last_request
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        self.last_request = time.time()
    
    def load_symbol(self, symbol: str, instrument_key: str, interval: str, days_back: int = 30) -> pd.DataFrame:
        """Load intraday data from Upstox API."""
        self._rate_limit()
        
        max_days = Config.UPSTOX_MAX_DAYS.get(interval, 30)
        days_back = min(days_back, max_days)
        
        to_date = datetime.now().strftime('%Y-%m-%d')
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        encoded_key = quote(instrument_key, safe='')
        url = f"{Config.UPSTOX_BASE_URL}/historical-candle/{encoded_key}/{interval}/{to_date}/{from_date}"
        
        try:
            response = self.session.get(url, timeout=30)
            
            if response.status_code != 200:
                return pd.DataFrame()
            
            data = response.json()
            
            if data.get('status') != 'success' or not data.get('data', {}).get('candles'):
                return pd.DataFrame()
            
            candles = data['data']['candles']
            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'oi'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.drop(columns=['oi'])
            
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            self.logger.debug(f"Upstox error for {symbol}: {e}")
            return pd.DataFrame()
    
    def close(self):
        self.session.close()


# =============================================================================
# CHECKPOINT
# =============================================================================

class Checkpoint:
    def __init__(self, interval: str, source: str):
        self.interval = interval
        self.source = source
        self.file = os.path.join(Config.CHECKPOINT_DIR, f"intraday_{source}_{interval}_checkpoint.json")
        os.makedirs(Config.CHECKPOINT_DIR, exist_ok=True)
    
    def load(self) -> dict:
        if os.path.exists(self.file):
            with open(self.file) as f:
                return json.load(f)
        return {"completed": [], "failed": [], "stats": {"inserted": 0, "skipped": 0}}
    
    def save(self, data: dict):
        data['last_updated'] = datetime.now().isoformat()
        with open(self.file, 'w') as f:
            json.dump(data, f, indent=2)


# =============================================================================
# MAIN ETL
# =============================================================================

class IntradayETL:
    def __init__(self, interval: str, source: str, token: str = None):
        self.interval = interval
        self.source = source
        self.db_interval = Config.INTERVAL_MAP.get(interval, interval)
        
        self.logger = setup_logging()
        self.db = Database(self.logger)
        self.checkpoint = Checkpoint(interval, source)
        
        if source == 'upstox':
            self.loader = UpstoxLoader(token, self.logger)
        else:
            self.loader = YFinanceLoader(self.logger)
        
        self.symbols = list(NIFTY_500_MAPPING.items())
    
    def run(self, resume: bool = True, max_symbols: int = None):
        self.logger.info("=" * 60)
        self.logger.info(f"INTRADAY ETL: {self.interval} via {self.source}")
        self.logger.info("=" * 60)
        
        # Load checkpoint
        state = self.checkpoint.load() if resume else {"completed": [], "failed": [], "stats": {"inserted": 0, "skipped": 0}}
        completed = set(state.get("completed", []))
        
        # Filter pending symbols
        pending = [(s, k) for s, k in self.symbols if s not in completed]
        
        if max_symbols:
            pending = pending[:max_symbols]
        
        self.logger.info(f"Total: {len(self.symbols)}, Completed: {len(completed)}, Pending: {len(pending)}")
        
        try:
            for i, (symbol, instrument_key) in enumerate(pending):
                self.logger.info(f"[{i+1}/{len(pending)}] {symbol}...")
                
                try:
                    if self.source == 'upstox':
                        df = self.loader.load_symbol(symbol, instrument_key, self.interval)
                    else:
                        df = self.loader.load_symbol(symbol, self.interval)
                    
                    if df.empty:
                        state["failed"].append(symbol)
                        self.logger.warning(f"  ✗ No data")
                        continue
                    
                    inserted, skipped = self.db.insert_candles(df, symbol, self.db_interval)
                    state["stats"]["inserted"] += inserted
                    state["stats"]["skipped"] += skipped
                    state["completed"].append(symbol)
                    
                    self.logger.info(f"  ✓ {inserted} candles (skipped {skipped})")
                    
                except Exception as e:
                    state["failed"].append(symbol)
                    self.logger.error(f"  ✗ Error: {e}")
                
                # Save checkpoint every 10 symbols
                if (i + 1) % 10 == 0:
                    self.checkpoint.save(state)
                
                # Rate limiting
                time.sleep(Config.YFINANCE_DELAY if self.source == 'yfinance' else 0.1)
            
            self.checkpoint.save(state)
            
        except KeyboardInterrupt:
            self.logger.warning("Interrupted. Saving checkpoint...")
            self.checkpoint.save(state)
        
        # Summary (before closing db)
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Completed: {len(state['completed'])}")
        self.logger.info(f"Failed: {len(state['failed'])}")
        self.logger.info(f"Inserted: {state['stats']['inserted']}")
        self.logger.info(f"Skipped: {state['stats']['skipped']}")
        
        try:
            symbol_count = self.db.get_symbol_count(self.db_interval)
            self.logger.info(f"DB symbols ({self.db_interval}): {symbol_count}")
        except:
            pass
        
        # Cleanup
        if hasattr(self.loader, 'close'):
            self.loader.close()
        self.db.close()


def main():
    parser = argparse.ArgumentParser(description="Intraday ETL Pipeline")
    parser.add_argument("--interval", choices=["1m", "5m", "15m", "30m"], default="5m")
    parser.add_argument("--source", choices=["yfinance", "upstox"], default="yfinance")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--fresh", action="store_true", help="Start fresh")
    parser.add_argument("--max", type=int, help="Max symbols to process")
    parser.add_argument("--token", help="Upstox access token")
    parser.add_argument("--all-intraday", action="store_true", help="Load all intraday intervals")
    
    args = parser.parse_args()
    
    # Load token from .env
    token = args.token
    if not token:
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("UPSTOX_ACCESS_TOKEN="):
                        token = line.split("=", 1)[1].strip()
                        break
    
    if args.all_intraday:
        # Load all intraday intervals using appropriate sources
        configs = [
            ("5m", "yfinance"),
            ("15m", "yfinance"),
            ("30m", "yfinance"),
        ]
        for interval, source in configs:
            print(f"\n{'='*60}")
            print(f"Loading {interval} ({source})")
            print(f"{'='*60}\n")
            etl = IntradayETL(interval, source, token)
            etl.run(resume=not args.fresh, max_symbols=args.max)
    else:
        etl = IntradayETL(args.interval, args.source, token)
        etl.run(resume=args.resume and not args.fresh, max_symbols=args.max)


if __name__ == "__main__":
    main()
