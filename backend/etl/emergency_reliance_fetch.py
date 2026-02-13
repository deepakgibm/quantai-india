import requests
import psycopg2
import os
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

# Load .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def get_intraday_reliance():
    # RELIANCE Instrument Key
    instrument_key = "NSE_EQ|INE002A01018"
    # Endpoints
    # 1. Intraday 1m
    url_1m = f"https://api.upstox.com/v3/historical-candle/intraday/{instrument_key}/minutes/1"
    # 2. Intraday 1d
    url_1d = f"https://api.upstox.com/v3/historical-candle/intraday/{instrument_key}/days/1"
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    print(f"Fetching Intraday 1m for RELIANCE...")
    r_1m = requests.get(url_1m, headers=headers)
    data_1m = r_1m.json()
    
    print(f"Fetching Intraday 1d for RELIANCE...")
    r_1d = requests.get(url_1d, headers=headers)
    data_1d = r_1d.json()

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    # RELIANCE ID
    cur.execute("SELECT instrument_id FROM instrument_master WHERE symbol = 'RELIANCE' LIMIT 1")
    inst_id = cur.fetchone()[0]

    count_1m = 0
    if data_1m.get("status") == "success":
        candles = data_1m["data"]["candles"]
        print(f"Found {len(candles)} intraday 1m candles.")
        for c in candles:
            # c = [timestamp, open, high, low, close, volume, oi]
            try:
                cur.execute("""
                    INSERT INTO stock_candle_history (instrument_id, candle_ts, open, high, low, close, volume, timeframe)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
                    ON CONFLICT (instrument_id, timeframe, candle_ts) DO NOTHING
                """, (inst_id, c[0], c[1], c[2], c[3], c[4], c[5]))
                count_1m += cur.rowcount
            except Exception as e:
                pass
    
    count_1d = 0
    if data_1d.get("status") == "success":
        candles = data_1d["data"]["candles"]
        print(f"Found {len(candles)} intraday 1d candles.")
        for c in candles:
            try:
                cur.execute("""
                    INSERT INTO stock_candle_history (instrument_id, candle_ts, open, high, low, close, volume, timeframe)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 1440)
                    ON CONFLICT (instrument_id, timeframe, candle_ts) DO NOTHING
                """, (inst_id, c[0], c[1], c[2], c[3], c[4], c[5]))
                count_1d += cur.rowcount
            except Exception as e:
                pass

    conn.commit()
    print(f"Inserted {count_1m} new 1m rows and {count_1d} new 1d rows for RELIANCE.")
    conn.close()

if __name__ == "__main__":
    get_intraday_reliance()
