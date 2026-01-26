"""
ETL: NIFTY 500 historical candles → PostgreSQL

FEATURES:
- Multi-timeframe (5m, 15m, 30m, 1H, 1D)
- V3 REST compliant
- Idempotent inserts (ON CONFLICT DO NOTHING)
- Auto-resume from last available data in database
- Token from .env file
- Unified Table Support:
  - Partitioned: stock_candle (instrument_id, timeframe SMALLINT, candle_ts)
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
DEFAULT_START_DATE = date(2026, 1, 10)

# Two weeks back from today
TWO_WEEKS_AGO = date.today() - timedelta(days=14)

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Accept": "application/json"
}

MAX_RETRIES = 5
RATE_LIMIT_SLEEP = 0.7



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

    conn.commit()
    print("[INFO] Database tables initialized (checkpoints)")
    return cur

# ==========================
# DATA FRESHNESS CHECK
# ==========================

def get_last_data_date(cur, instrument_key, timeframe, instrument_id=None, tf_minutes=None):
    """
    Get the last available data date for an instrument+timeframe from the database.
    Returns None if no data exists.
    """
    if instrument_id and tf_minutes:
        cur.execute("""
            SELECT MAX(candle_ts::date) 
            FROM stock_candle 
            WHERE instrument_id = %s AND timeframe = %s
        """, (instrument_id, tf_minutes))
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
        # Data is stale (older than 2 weeks) - CAP AT TWO WEEKS
        print(f"  [STALE] {symbol}/{timeframe}: Last data {last_date}, CAP AT {TWO_WEEKS_AGO}")
        return TWO_WEEKS_AGO

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
# INTRADAY API (for today's data)
# ==========================

INTRADAY_BASE_URL = "https://api.upstox.com/v3/historical-candle/intraday"

def fetch_intraday_candles(instrument_key, unit, interval):
    """
    Fetch today's candles from Upstox Intraday Candle V3 API.
    
    This endpoint returns candles for the CURRENT TRADING DAY only.
    Unlike the historical endpoint, it doesn't require date parameters.
    
    Args:
        instrument_key: e.g., "NSE_EQ|INE002A01018"
        unit: "minutes", "hours", or "days"
        interval: "1", "5", "15", "30" for minutes; "1" for hours/days
    
    Returns:
        dict with 'data' -> 'candles' array
    """
    url = f"{INTRADAY_BASE_URL}/{instrument_key}/{unit}/{interval}"

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
            if e.response.status_code == 400:
                # Some instruments don't support intraday data
                return {"data": {"candles": []}}
            wait = 2 ** attempt
            print(f"[WARN] {e} → retry in {wait}s")
            time.sleep(wait)
        except Exception as e:
            wait = 2 ** attempt
            print(f"[WARN] {e} → retry in {wait}s")
            time.sleep(wait)

    return {"data": {"candles": []}}  # Return empty on failure

# ==========================
# LOAD SYMBOLS FROM INSTRUMENT_MASTER
# ==========================

def load_symbols_from_db(conn):
    """
    Load symbols from instrument_master table instead of CSV.
    This ensures we use the database as the source of truth.
    
    Returns:
        List of dicts with symbol, instrument_key, instrument_id
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            symbol, 
            instrument_key, 
            instrument_id,
            company_name
        FROM instrument_master
        WHERE is_active = TRUE 
          AND exchange = 'NSE' 
          AND series IN ('EQ', 'INDEX')
        ORDER BY symbol
    """)
    
    rows = cur.fetchall()
    symbols = []
    for row in rows:
        symbols.append({
            "symbol": row[0],
            "instrument_key": row[1],
            "instrument_id": row[2],
            "company_name": row[3] or row[0]
        })
    
    return symbols


def load_symbols():
    """Load symbols from CSV file (legacy fallback)."""
    if not SYMBOL_FILE.exists():
        return []
    
    with open(SYMBOL_FILE, newline="") as f:
        return list(csv.DictReader(f))


def find_missing_symbols(conn, tf_minutes: int = 1440):
    """
    Find symbols in instrument_master that have NO data in stock_candle.
    
    Args:
        conn: Database connection
        tf_minutes: Timeframe to check (default: 1d = 1440 minutes)
    
    Returns:
        List of symbols with no candle data
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            im.symbol, 
            im.instrument_key, 
            im.instrument_id,
            im.company_name
        FROM instrument_master im
        LEFT JOIN (
            SELECT DISTINCT instrument_id 
            FROM stock_candle 
            WHERE timeframe = %s
        ) sc ON im.instrument_id = sc.instrument_id
        WHERE im.is_active = TRUE 
          AND im.exchange = 'NSE' 
          AND im.series IN ('EQ', 'INDEX')
          AND sc.instrument_id IS NULL
        ORDER BY im.symbol
    """, (tf_minutes,))
    
    rows = cur.fetchall()
    missing = []
    for row in rows:
        missing.append({
            "symbol": row[0],
            "instrument_key": row[1],
            "instrument_id": row[2],
            "company_name": row[3] or row[0]
        })
    
    return missing


def find_stale_symbols(conn, tf_minutes: int = 1440, days_threshold: int = 14):
    """
    Find symbols in stock_candle that have stale data (older than threshold).
    
    Args:
        conn: Database connection
        tf_minutes: Timeframe to check (default: 1d = 1440 minutes)
        days_threshold: Data older than this is considered stale
    
    Returns:
        List of symbols with stale data and their last candle date
    """
    cur = conn.cursor()
    threshold_date = date.today() - timedelta(days=days_threshold)
    
    cur.execute("""
        SELECT 
            im.symbol, 
            im.instrument_key, 
            im.instrument_id,
            MAX(sc.candle_ts) as last_candle
        FROM instrument_master im
        JOIN stock_candle sc ON im.instrument_id = sc.instrument_id
        WHERE im.is_active = TRUE 
          AND im.exchange = 'NSE' 
          AND im.series IN ('EQ', 'INDEX')
          AND sc.timeframe = %s
        GROUP BY im.symbol, im.instrument_key, im.instrument_id
        HAVING MAX(sc.candle_ts) < %s
        ORDER BY MAX(sc.candle_ts)
    """, (tf_minutes, threshold_date))
    
    rows = cur.fetchall()
    stale = []
    for row in rows:
        stale.append({
            "symbol": row[0],
            "instrument_key": row[1],
            "instrument_id": row[2],
            "last_candle": row[3]
        })
    
    return stale

def run_etl(symbols_filter=None, intervals_filter=None, use_db_source=True, missing_only=False):
    """
    Run the ETL process.
    
    Args:
        symbols_filter: Optional list of symbols to process (e.g., ["RELIANCE", "TCS"])
        intervals_filter: Optional list of intervals to process (e.g., ["1d", "1h"])
        use_db_source: If True, load symbols from instrument_master (recommended)
        missing_only: If True, only process symbols with missing candle data
    """
    conn = get_connection()
    cur = init_db(conn)
    today = date.today()

    # Load symbols - prefer instrument_master over CSV
    if use_db_source:
        if missing_only:
            symbols = find_missing_symbols(conn, tf_minutes=1440)
            print(f"[INFO] Found {len(symbols)} symbols with MISSING data in stock_candle")
        else:
            symbols = load_symbols_from_db(conn)
            print(f"[INFO] Loaded {len(symbols)} active symbols from instrument_master")
    else:
        symbols = load_symbols()
        print(f"[INFO] Loaded {len(symbols)} symbols from {SYMBOL_FILE} (legacy mode)")
    
    print(f"[INFO] Token length: {len(ACCESS_TOKEN)} chars")
    print(f"[INFO] Two weeks ago: {TWO_WEEKS_AGO}")
    print(f"[INFO] Today: {today}")
    print(f"[INFO] Target table: stock_candle\n")

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
        
        # Use pre-loaded instrument_id if available (from instrument_master query)
        instrument_id = sym.get("instrument_id")

        print(f"\n{'='*50}")
        print(f"Processing: {symbol}")
        print(f"Instrument: {instrument_key}")
        
        # instrument_id resolution
        if not instrument_id:
            try:
                instrument_id = resolve_by_instrument_key(instrument_key)
                if instrument_id:
                    print(f"Resolved instrument_id: {instrument_id}")
                else:
                    print(f"[WARN] Could not resolve instrument_id for {symbol}")
            except Exception as resolve_error:
                print(f"[WARN] instrument_id resolution failed: {resolve_error}")
        else:
            print(f"Using instrument_id: {instrument_id} (from instrument_master)")
        
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
                
                if start_date > today:
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
                                if instrument_id:
                                    # stock_candle with instrument_id
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
                                    # Fallback for when ID resolution fails - log error but don't crash
                                    errors.append(f"{symbol}: No instrument_id for insertion")
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
                
                # ========================================
                # INTRADAY FETCH: Get today's candles
                # ========================================
                # The historical API doesn't return today's data.
                # Use the Intraday API to fetch current day's candles.
                try:
                    intraday_data = fetch_intraday_candles(
                        instrument_key,
                        cfg["unit"],
                        cfg["interval"]
                    )
                    
                    intraday_candles = intraday_data.get("data", {}).get("candles", [])
                    
                    if intraday_candles:
                        intraday_rows = 0
                        for c in intraday_candles:
                            try:
                                if instrument_id:
                                    cur.execute("""
                                        INSERT INTO stock_candle 
                                        (instrument_id, timeframe, candle_ts, open, high, low, close, volume)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                        ON CONFLICT (instrument_id, timeframe, candle_ts) DO NOTHING
                                    """, (
                                        instrument_id,
                                        tf_minutes,
                                        c[0],
                                        c[1],
                                        c[2],
                                        c[3],
                                        c[4],
                                        c[5],
                                    ))
                                intraday_rows += 1
                            except Exception as intraday_insert_err:
                                pass  # Likely duplicate, ignore
                        
                        conn.commit()
                        if intraday_rows > 0:
                            print(f"  [INTRADAY] {symbol}/{tf}: {len(intraday_candles)} today's candles")
                            total_rows += intraday_rows
                            
                except Exception as intraday_error:
                    print(f"  [WARN] Intraday fetch failed: {intraday_error}")
                
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
    
    parser = argparse.ArgumentParser(description="NIFTY 500 Candle ETL to PostgreSQL (stock_candle table)")
    parser.add_argument("--symbols", nargs="+", help="Specific symbols to process (e.g., RELIANCE TCS)")
    parser.add_argument("--intervals", nargs="+", help="Specific intervals to process (e.g., 1d 1h)")
    parser.add_argument("--check-only", action="store_true", help="Only check data freshness, don't load")
    parser.add_argument("--use-csv", action="store_true", help="Use CSV file instead of instrument_master (legacy mode)")
    parser.add_argument("--missing-only", action="store_true", help="Only process symbols with NO candle data")
    parser.add_argument("--show-missing", action="store_true", help="Show symbols with missing data and exit")
    parser.add_argument("--show-stale", action="store_true", help="Show symbols with stale data and exit")
    
    args = parser.parse_args()
    
    if args.show_missing:
        # Show symbols with missing data
        conn = get_connection()
        cur = init_db(conn)
        
        print("\n[MISSING SYMBOLS - No data in stock_candle for 1d timeframe]")
        print("="*60)
        
        missing = find_missing_symbols(conn, tf_minutes=1440)
        print(f"Found {len(missing)} symbols with NO candle data:\n")
        
        for sym in missing[:50]:  # Show first 50
            print(f"  - {sym['symbol']:15} (ID: {sym['instrument_id']})")
        
        if len(missing) > 50:
            print(f"\n  ... and {len(missing) - 50} more")
        
        conn.close()
        
    elif args.show_stale:
        # Show symbols with stale data
        conn = get_connection()
        cur = init_db(conn)
        
        print("\n[STALE SYMBOLS - Data older than 14 days in stock_candle]")
        print("="*60)
        
        stale = find_stale_symbols(conn, tf_minutes=1440, days_threshold=14)
        print(f"Found {len(stale)} symbols with STALE candle data:\n")
        
        for sym in stale[:50]:  # Show first 50
            print(f"  - {sym['symbol']:15} Last: {sym['last_candle']}")
        
        if len(stale) > 50:
            print(f"\n  ... and {len(stale) - 50} more")
        
        conn.close()
        
    elif args.check_only:
        # Just check data freshness
        conn = get_connection()
        cur = init_db(conn)
        
        # Use DB source by default
        if args.use_csv:
            symbols = load_symbols()
        else:
            symbols = load_symbols_from_db(conn)
        
        print("\n[DATA FRESHNESS CHECK - stock_candle table]")
        print("="*60)
        
        for sym in symbols[:10]:  # Check first 10
            symbol = sym["symbol"]
            instrument_key = sym["instrument_key"]
            instrument_id = sym.get("instrument_id")
            
            for cfg in INTERVALS:
                tf_minutes = cfg["tf_minutes"]
                db_timeframe = cfg["db_timeframe"]
                
                # Check new schema first
                if instrument_id and USE_NEW_SCHEMA:
                    cur.execute("""
                        SELECT MAX(candle_ts)::date FROM stock_candle 
                        WHERE instrument_id = %s AND timeframe = %s
                    """, (instrument_id, tf_minutes))
                    result = cur.fetchone()
                    last_date = result[0] if result else None
                else:
                    last_date = get_last_data_date(cur, instrument_key, db_timeframe)
                
                status = "✓" if last_date and last_date >= TWO_WEEKS_AGO else "✗"
                print(f"{status} {symbol}/{db_timeframe}: {last_date or 'NO DATA'}")
        
        conn.close()
    else:
        run_etl(
            symbols_filter=args.symbols,
            intervals_filter=args.intervals,
            use_db_source=not args.use_csv,
            missing_only=args.missing_only
        )

