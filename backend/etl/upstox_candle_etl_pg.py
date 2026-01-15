"""
ETL: NIFTY 500 historical candles → PostgreSQL

FEATURES:
- Multi-timeframe (5m, 15m, 30m, 1H, 1D)
- V3 REST compliant
- Idempotent inserts (ON CONFLICT DO NOTHING)
- Auto-resume from last available data in database
- Token from .env file
- DUAL TABLE SUPPORT:
  - Legacy: stock_candles (symbol, instrument_key, timeframe TEXT)
  - New: stock_candle (instrument_id, timeframe SMALLINT, candle_ts)
"""

import csv
import os
import sys
import time
import requests
import psycopg2
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.instrument_resolver import resolve_by_instrument_key
from services.timeframe_converter import text_to_minutes

# ==========================
# LOAD ENVIRONMENT
# ==========================

# Load .env from backend directory
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[INFO] Loaded .env from {env_path}")
else:
    # Try current directory
    load_dotenv()
    print("[INFO] Loaded .env from current directory")

# ==========================
# CONFIG
# ==========================

ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
if not ACCESS_TOKEN:
    raise ValueError("UPSTOX_ACCESS_TOKEN not found in .env file")

# PostgreSQL connection - local database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/quantai")
# Convert asyncpg URL to psycopg2 format
SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

BASE_URL = "https://api.upstox.com/v3/historical-candle"

SYMBOL_FILE = Path(__file__).parent / "nifty_500.csv"

# Default start date - will be overridden by database check
DEFAULT_START_DATE = date(2022, 1, 1)

# Two weeks back from today
TWO_WEEKS_AGO = date.today() - timedelta(days=14)

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Accept": "application/json"
}

MAX_RETRIES = 5
RATE_LIMIT_SLEEP = 0.7

# Flag to control which table to write to
USE_NEW_SCHEMA = True  # Set to True to use new stock_candle table

# Interval config - includes tf_minutes for new schema
INTERVALS = [
    {"tf": "5m",  "unit": "minutes", "interval": "5",  "window": "month",   "db_timeframe": "5m",  "tf_minutes": 5},
    {"tf": "15m", "unit": "minutes", "interval": "15", "window": "month",   "db_timeframe": "15m", "tf_minutes": 15},
    {"tf": "30m", "unit": "minutes", "interval": "30", "window": "quarter", "db_timeframe": "30m", "tf_minutes": 30},
    {"tf": "1h",  "unit": "hours",   "interval": "1",  "window": "quarter", "db_timeframe": "1h",  "tf_minutes": 60},
    {"tf": "1d",  "unit": "days",    "interval": "1",  "window": "year",    "db_timeframe": "1d",  "tf_minutes": 1440},
]

# ==========================
# WINDOW GENERATORS
# ==========================

def month_windows(start, end):
    cur = start
    while cur < end:
        nxt = cur + relativedelta(months=1)
        yield cur, min(nxt, end)
        cur = nxt

def quarter_windows(start, end):
    cur = start
    while cur < end:
        nxt = cur + relativedelta(months=3)
        yield cur, min(nxt, end)
        cur = nxt

def year_windows(start, end):
    cur = start
    while cur < end:
        nxt = cur + relativedelta(years=1)
        yield cur, min(nxt, end)
        cur = nxt

# ==========================
# DB SETUP
# ==========================

def get_connection():
    """Get PostgreSQL connection."""
    print(f"[INFO] Connecting to PostgreSQL: {SYNC_DATABASE_URL.split('@')[1]}")
    return psycopg2.connect(SYNC_DATABASE_URL)

def init_db(conn):
    """Initialize database tables if they don't exist."""
    cur = conn.cursor()

    # Create stock_candles table if not exists
    # Schema matches models_alpha.py StockCandle model
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_candles (
            symbol TEXT NOT NULL,
            instrument_key TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            PRIMARY KEY (instrument_key, timeframe, timestamp)
        )
    """)

    # Create ingestion_checkpoint table for resume capability
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ingestion_checkpoint (
            instrument_key VARCHAR(100),
            timeframe VARCHAR(10),
            last_date DATE,
            updated_at TIMESTAMP,
            PRIMARY KEY (instrument_key, timeframe)
        )
    """)

    # Create indexes for faster lookups
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_stock_candles_symbol_tf 
        ON stock_candles(symbol, timeframe, timestamp DESC)
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_stock_candles_instrument_tf 
        ON stock_candles(instrument_key, timeframe, timestamp DESC)
    """)

    conn.commit()
    print("[INFO] Database tables initialized (stock_candles)")
    return cur

# ==========================
# DATA FRESHNESS CHECK
# ==========================

def get_last_data_date(cur, instrument_key, timeframe, instrument_id=None, tf_minutes=None):
    """
    Get the last available data date for an instrument+timeframe from the database.
    Returns None if no data exists.
    
    Checks new schema first (if instrument_id provided), falls back to legacy.
    """
    # Try new schema first
    if USE_NEW_SCHEMA and instrument_id and tf_minutes:
        cur.execute("""
            SELECT MAX(candle_ts::date) 
            FROM stock_candle 
            WHERE instrument_id = %s AND timeframe = %s
        """, (instrument_id, tf_minutes))
        row = cur.fetchone()
        if row and row[0]:
            return row[0]
    
    # Fallback to legacy schema
    cur.execute("""
        SELECT MAX(timestamp::date) 
        FROM stock_candles 
        WHERE instrument_key = %s AND timeframe = %s
    """, (instrument_key, timeframe))
    row = cur.fetchone()
    if row and row[0]:
        return row[0]
    return None

def check_data_freshness(cur, instrument_key, symbol, timeframe, instrument_id=None, tf_minutes=None):
    """
    Check if data exists up to two weeks back.
    Returns the date to resume from.
    """
    last_date = get_last_data_date(cur, instrument_key, timeframe, instrument_id, tf_minutes)
    
    if last_date is None:
        # No data exists, start from default
        print(f"  [NEW] {symbol}/{timeframe}: No existing data, starting from {DEFAULT_START_DATE}")
        return DEFAULT_START_DATE
    
    if last_date >= TWO_WEEKS_AGO:
        # Data is fresh enough (within 2 weeks)
        print(f"  [FRESH] {symbol}/{timeframe}: Data up to {last_date}, resuming from next day")
        return last_date + timedelta(days=1)
    else:
        # Data is stale (older than 2 weeks)
        print(f"  [STALE] {symbol}/{timeframe}: Last data {last_date}, resuming from next day")
        return last_date + timedelta(days=1)

# ==========================
# CHECKPOINT HELPERS
# ==========================

def get_checkpoint(cur, instrument_key, timeframe):
    """Get checkpoint from database."""
    cur.execute("""
        SELECT last_date FROM ingestion_checkpoint
        WHERE instrument_key = %s AND timeframe = %s
    """, (instrument_key, timeframe))
    row = cur.fetchone()
    if row:
        return row[0]
    return None

def update_checkpoint(cur, instrument_key, timeframe, last_date):
    """Update checkpoint in database."""
    cur.execute("""
        INSERT INTO ingestion_checkpoint (instrument_key, timeframe, last_date, updated_at)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (instrument_key, timeframe)
        DO UPDATE SET
            last_date = EXCLUDED.last_date,
            updated_at = EXCLUDED.updated_at
    """, (
        instrument_key,
        timeframe,
        last_date,
        datetime.utcnow()
    ))

# ==========================
# API FETCH
# ==========================

def fetch_candles(instrument_key, unit, interval, from_date, to_date):
    """Fetch candles from Upstox V3 API."""
    url = (
        f"{BASE_URL}/"
        f"{instrument_key}/"
        f"{unit}/"
        f"{interval}/"
        f"{to_date}/{from_date}"
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            
            if r.status_code == 429:
                wait = 2 ** attempt
                print(f"[WARN] Rate limited → retry in {wait}s")
                time.sleep(wait)
                continue
                
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("[ERROR] Token expired! Please refresh UPSTOX_ACCESS_TOKEN in .env")
                raise
            wait = 2 ** attempt
            print(f"[WARN] {e} → retry in {wait}s")
            time.sleep(wait)
        except Exception as e:
            wait = 2 ** attempt
            print(f"[WARN] {e} → retry in {wait}s")
            time.sleep(wait)

    raise RuntimeError("Max retries exceeded")

# ==========================
# LOAD SYMBOLS
# ==========================

def load_symbols():
    """Load symbols from CSV file."""
    if not SYMBOL_FILE.exists():
        raise FileNotFoundError(f"Symbol file not found: {SYMBOL_FILE}")
    
    with open(SYMBOL_FILE, newline="") as f:
        return list(csv.DictReader(f))

# ==========================
# ETL
# ==========================

def run_etl(symbols_filter=None, intervals_filter=None):
    """
    Run the ETL process.
    
    Args:
        symbols_filter: Optional list of symbols to process (e.g., ["RELIANCE", "TCS"])
        intervals_filter: Optional list of intervals to process (e.g., ["1d", "1h"])
    """
    conn = get_connection()
    cur = init_db(conn)
    today = date.today()

    symbols = load_symbols()
    print(f"[INFO] Loaded {len(symbols)} symbols from {SYMBOL_FILE}")
    print(f"[INFO] Token length: {len(ACCESS_TOKEN)} chars")
    print(f"[INFO] Two weeks ago: {TWO_WEEKS_AGO}")
    print(f"[INFO] Today: {today}")
    print(f"[INFO] New schema mode: {USE_NEW_SCHEMA}")
    print(f"[INFO] Target table: {'stock_candle (new)' if USE_NEW_SCHEMA else 'stock_candles (legacy)'}\n")

    # Filter symbols if specified
    if symbols_filter:
        symbols = [s for s in symbols if s["symbol"] in symbols_filter]
        print(f"[INFO] Filtered to {len(symbols)} symbols: {symbols_filter}")

    total_rows = 0
    errors = []
    skipped_instruments = []

    for sym in symbols:
        symbol = sym["symbol"]
        instrument_key = sym["instrument_key"]

        print(f"\n{'='*50}")
        print(f"Processing: {symbol}")
        print(f"Instrument: {instrument_key}")
        
        # Resolve instrument_id for new schema
        instrument_id = None
        if USE_NEW_SCHEMA:
            try:
                instrument_id = resolve_by_instrument_key(instrument_key)
                if instrument_id:
                    print(f"Resolved instrument_id: {instrument_id}")
                else:
                    print(f"[WARN] Could not resolve instrument_id, will use legacy table")
            except Exception as resolve_error:
                print(f"[WARN] instrument_id resolution failed: {resolve_error}")
        
        print(f"{'='*50}")

        for cfg in INTERVALS:
            tf = cfg["tf"]
            db_timeframe = cfg["db_timeframe"]
            tf_minutes = cfg["tf_minutes"]
            
            # Filter intervals if specified
            if intervals_filter and tf not in intervals_filter:
                continue

            print(f"\n[TF] {tf} → DB timeframe: {db_timeframe} ({tf_minutes} min)")

            try:
                # Check data freshness and determine start date
                start_date = check_data_freshness(
                    cur, instrument_key, symbol, db_timeframe,
                    instrument_id=instrument_id, tf_minutes=tf_minutes
                )
                
                if start_date >= today:
                    print(f"  [SKIP] Already up-to-date")
                    continue

                window_fn = {
                    "month": month_windows,
                    "quarter": quarter_windows,
                    "year": year_windows
                }[cfg["window"]]

                window_rows = 0
                for start, end in window_fn(start_date, today):
                    try:
                        data = fetch_candles(
                            instrument_key,
                            cfg["unit"],
                            cfg["interval"],
                            start.isoformat(),
                            end.isoformat()
                        )

                        candles = data.get("data", {}).get("candles", [])
                        if not candles:
                            update_checkpoint(cur, instrument_key, tf, end)
                            conn.commit()
                            continue

                        # Insert into appropriate table based on schema mode
                        for c in candles:
                            try:
                                if USE_NEW_SCHEMA and instrument_id:
                                    # NEW SCHEMA: stock_candle with instrument_id
                                    cur.execute("""
                                        INSERT INTO stock_candle 
                                        (instrument_id, timeframe, candle_ts, open, high, low, close, volume)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                        ON CONFLICT (instrument_id, timeframe, candle_ts) DO NOTHING
                                    """, (
                                        instrument_id,     # instrument_id (BIGINT)
                                        tf_minutes,        # timeframe (SMALLINT minutes)
                                        c[0],              # candle_ts (TIMESTAMP)
                                        c[1],              # open
                                        c[2],              # high
                                        c[3],              # low
                                        c[4],              # close
                                        c[5],              # volume
                                    ))
                                else:
                                    # LEGACY SCHEMA: stock_candles with symbol
                                    cur.execute("""
                                        INSERT INTO stock_candles 
                                        (symbol, instrument_key, timeframe, timestamp, open, high, low, close, volume)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                        ON CONFLICT (instrument_key, timeframe, timestamp) DO NOTHING
                                    """, (
                                        symbol,            # symbol (company name)
                                        instrument_key,    # instrument_key (NSE_EQ|...)
                                        db_timeframe,      # timeframe (1d, 1h, 5m, etc.)
                                        c[0],              # timestamp
                                        c[1],              # open
                                        c[2],              # high
                                        c[3],              # low
                                        c[4],              # close
                                        c[5],              # volume
                                    ))
                            except Exception as insert_error:
                                print(f"  [WARN] Insert error: {insert_error}")

                        update_checkpoint(cur, instrument_key, tf, end)
                        conn.commit()

                        window_rows += len(candles)
                        print(f"  [OK] {start} → {end}: {len(candles)} rows")
                        time.sleep(RATE_LIMIT_SLEEP)

                    except Exception as window_error:
                        print(f"  [ERROR] Window {start}-{end}: {window_error}")
                        errors.append(f"{symbol}/{tf}: {window_error}")
                        continue

                total_rows += window_rows
                print(f"  [TOTAL] {symbol}/{tf}: {window_rows} rows inserted")

            except Exception as tf_error:
                print(f"  [ERROR] {symbol}/{tf}: {tf_error}")
                errors.append(f"{symbol}/{tf}: {tf_error}")
                continue

    conn.close()

    
    print(f"\n{'='*50}")
    print(f"ETL COMPLETED")
    print(f"{'='*50}")
    print(f"Total rows inserted: {total_rows}")
    print(f"Errors: {len(errors)}")
    if errors:
        print("\nErrors encountered:")
        for e in errors[:10]:  # Show first 10 errors
            print(f"  - {e}")

# ==========================
# MAIN
# ==========================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="NIFTY 500 Candle ETL to PostgreSQL (stock_candles table)")
    parser.add_argument("--symbols", nargs="+", help="Specific symbols to process (e.g., RELIANCE TCS)")
    parser.add_argument("--intervals", nargs="+", help="Specific intervals to process (e.g., 1d 1h)")
    parser.add_argument("--check-only", action="store_true", help="Only check data freshness, don't load")
    
    args = parser.parse_args()
    
    if args.check_only:
        # Just check data freshness
        conn = get_connection()
        cur = init_db(conn)
        symbols = load_symbols()
        
        print("\n[DATA FRESHNESS CHECK - stock_candles table]")
        print("="*60)
        
        for sym in symbols[:10]:  # Check first 10
            symbol = sym["symbol"]
            instrument_key = sym["instrument_key"]
            for cfg in INTERVALS:
                db_timeframe = cfg["db_timeframe"]
                last_date = get_last_data_date(cur, instrument_key, db_timeframe)
                status = "✓" if last_date and last_date >= TWO_WEEKS_AGO else "✗"
                print(f"{status} {symbol}/{db_timeframe}: {last_date or 'NO DATA'}")
        
        conn.close()
    else:
        run_etl(
            symbols_filter=args.symbols,
            intervals_filter=args.intervals
        )
