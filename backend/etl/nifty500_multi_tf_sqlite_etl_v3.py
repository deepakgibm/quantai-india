"""
ETL: NIFTY 500 historical candles → SQLite
Features:
- Multi-timeframe (5m, 15m, 30m, 1H, 1D)
- V3 REST compliant
- Idempotent inserts
- Checkpointing (resume per symbol + TF)
"""

import csv
import time
import sqlite3
import requests
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

# ==========================
# CONFIG
# ==========================

ACCESS_TOKEN="eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI3NzYyMjgiLCJqdGkiOiI2OTRlNGJlMmQ0OWM4NDA1NDQyMWZhNmMiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlhdCI6MTc2NjczODkxNCwiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxNzY2Nzg2NDAwfQ.es0VXBDEQnJaQVFbRFH5xiBEXggt3hJOmojtWqGZEqg"
BASE_URL = "https://api.upstox.com/v3/historical-candle"

SYMBOL_FILE = "nifty_500.csv"
DB_NAME = "stock_data_v1.db"

DEFAULT_START_DATE = date(2022, 1, 1)

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Accept": "application/json"
}

MAX_RETRIES = 5
RATE_LIMIT_SLEEP = 0.7

INTERVALS = [
    {"tf": "5m",  "unit": "minutes", "interval": "5",  "window": "month"},
    {"tf": "15m", "unit": "minutes", "interval": "15", "window": "month"},
    {"tf": "30m", "unit": "minutes", "interval": "30", "window": "quarter"},
    {"tf": "1h",  "unit": "hours",   "interval": "1",  "window": "quarter"},
    {"tf": "1d",  "unit": "days",    "interval": "1",  "window": "year"},
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

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_candles (
            symbol TEXT,
            instrument_key TEXT,
            timeframe TEXT,
            timestamp TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            PRIMARY KEY (instrument_key, timeframe, timestamp)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ingestion_checkpoint (
            instrument_key TEXT,
            timeframe TEXT,
            last_date TEXT,
            updated_at TEXT,
            PRIMARY KEY (instrument_key, timeframe)
        )
    """)

    conn.commit()
    return conn

# ==========================
# CHECKPOINT HELPERS
# ==========================

def get_checkpoint(cur, instrument_key, timeframe):
    cur.execute("""
        SELECT last_date FROM ingestion_checkpoint
        WHERE instrument_key = ? AND timeframe = ?
    """, (instrument_key, timeframe))
    row = cur.fetchone()
    if row:
        return date.fromisoformat(row[0])
    return DEFAULT_START_DATE

def update_checkpoint(cur, instrument_key, timeframe, last_date):
    cur.execute("""
        INSERT INTO ingestion_checkpoint
        VALUES (?, ?, ?, ?)
        ON CONFLICT(instrument_key, timeframe)
        DO UPDATE SET
            last_date = excluded.last_date,
            updated_at = excluded.updated_at
    """, (
        instrument_key,
        timeframe,
        last_date.isoformat(),
        datetime.utcnow().isoformat()
    ))

# ==========================
# API FETCH
# ==========================

def fetch_candles(instrument_key, unit, interval, from_date, to_date):
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
            r.raise_for_status()
            return r.json()
        except Exception as e:
            wait = 2 ** attempt
            print(f"[WARN] {e} → retry in {wait}s")
            time.sleep(wait)

    raise RuntimeError("Max retries exceeded")

# ==========================
# LOAD SYMBOLS
# ==========================

def load_symbols():
    with open(SYMBOL_FILE, newline="") as f:
        return list(csv.DictReader(f))

# ==========================
# ETL
# ==========================

def run_etl():
    conn = init_db()
    cur = conn.cursor()
    today = date.today()

    symbols = load_symbols()
    print(f"[INFO] Loaded {len(symbols)} symbols")

    for sym in symbols:
        symbol = sym["symbol"]
        instrument_key = sym["instrument_key"]

        print(f"\n=== {symbol} ===")

        for cfg in INTERVALS:
            tf = cfg["tf"]
            print(f"[TF] {tf}")

            start_date = get_checkpoint(cur, instrument_key, tf)
            if start_date >= today:
                print("[SKIP] Already up-to-date")
                continue

            window_fn = {
                "month": month_windows,
                "quarter": quarter_windows,
                "year": year_windows
            }[cfg["window"]]

            for start, end in window_fn(start_date, today):
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

                rows = [
                    (
                        symbol,
                        instrument_key,
                        tf,
                        c[0], c[1], c[2], c[3], c[4], c[5]
                    )
                    for c in candles
                ]

                cur.executemany("""
                    INSERT OR IGNORE INTO stock_candles
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, rows)

                update_checkpoint(cur, instrument_key, tf, end)
                conn.commit()

                print(f"[INFO] {symbol} {tf} → {len(rows)} rows")
                time.sleep(RATE_LIMIT_SLEEP)

    conn.close()
    print("\n[SUCCESS] ETL completed with checkpointing")

# ==========================
# MAIN
# ==========================

if __name__ == "__main__":
    run_etl()
