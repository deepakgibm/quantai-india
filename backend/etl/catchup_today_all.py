import requests
import psycopg2
import os
import time
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

# Load .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def get_db_connection():
    return psycopg2.connect(DB_URL)

def resample_and_insert(conn, instrument_id, df_1m, target_tf_str, target_mins):
    """Resample 1m data and insert into stock_candle_history"""
    if df_1m.empty: return
    try:
        resample_df = df_1m.copy()
        resample_df.set_index('candle_ts', inplace=True)
        # Ensure it's datetime
        resample_df.index = pd.to_datetime(resample_df.index)
        
        agg_dict = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        resampled = resample_df.resample(target_tf_str).agg(agg_dict).dropna()
        
        cursor = conn.cursor()
        records = []
        for ts, row in resampled.iterrows():
            records.append((
                instrument_id, ts.to_pydatetime(), float(row['open']), float(row['high']),
                float(row['low']), float(row['close']), int(row['volume']),
                target_mins
            ))
        
        if not records: return
            
        args_str = ','.join(cursor.mogrify("(%s,%s,%s,%s,%s,%s,%s,%s)", x).decode('utf-8') for x in records)
        cursor.execute(f"""
            INSERT INTO stock_candle (instrument_id, candle_ts, open, high, low, close, volume, timeframe)
            VALUES {args_str}
            ON CONFLICT (instrument_id, timeframe, candle_ts) DO NOTHING
        """)
        conn.commit()
    except Exception as e:
        print(f"    ! Resample Error ({target_tf_str}): {e}")

def catchup_symbol(conn, symbol, instrument_key, instrument_id):
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    
    # 1. Fetch Intraday 1m
    url_1m = f"https://api.upstox.com/v3/historical-candle/intraday/{instrument_key}/minutes/1"
    # 2. Fetch Intraday 1d
    url_1d = f"https://api.upstox.com/v3/historical-candle/intraday/{instrument_key}/days/1"

    try:
        # Fetch 1m
        r_1m = requests.get(url_1m, headers=headers, timeout=10)
        data_1m = r_1m.json()
        
        if data_1m.get("status") == "success":
            candles = data_1m["data"]["candles"]
            if candles:
                df_1m = pd.DataFrame(candles, columns=["candle_ts", "open", "high", "low", "close", "volume", "oi"])
                df_1m["candle_ts"] = pd.to_datetime(df_1m["candle_ts"])
                
                # Bulk Insert 1m
                cur = conn.cursor()
                records = []
                for _, row in df_1m.iterrows():
                    records.append((
                        instrument_id, row['candle_ts'].to_pydatetime(), float(row['open']), float(row['high']),
                        float(row['low']), float(row['close']), int(row['volume']), 1
                    ))
                
                args_str = ','.join(cur.mogrify("(%s,%s,%s,%s,%s,%s,%s,%s)", x).decode('utf-8') for x in records)
                cur.execute(f"INSERT INTO stock_candle_history (instrument_id, candle_ts, open, high, low, close, volume, timeframe) VALUES {args_str} ON CONFLICT DO NOTHING")
                conn.commit()
                
                # Resample
                resample_and_insert(conn, instrument_id, df_1m, '3T', 3)
                resample_and_insert(conn, instrument_id, df_1m, '5T', 5)
                resample_and_insert(conn, instrument_id, df_1m, '15T', 15)
                resample_and_insert(conn, instrument_id, df_1m, '30T', 30)
                resample_and_insert(conn, instrument_id, df_1m, '1H', 60)
                print(f"  [OK] {symbol}: Sync'd 1m and resampled.")
        
        # Fetch 1d
        r_1d = requests.get(url_1d, headers=headers, timeout=10)
        data_1d = r_1d.json()
        if data_1d.get("status") == "success":
            candles = data_1d["data"]["candles"]
            if candles:
                cur = conn.cursor()
                for c in candles:
                    cur.execute("""
                        INSERT INTO stock_candle (instrument_id, candle_ts, open, high, low, close, volume, timeframe)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 1440)
                        ON CONFLICT (instrument_id, timeframe, candle_ts) DO NOTHING
                    """, (instrument_id, c[0], c[1], c[2], c[3], c[4], c[5]))
                conn.commit()
                print(f"  [OK] {symbol}: Sync'd Daily.")

    except Exception as e:
        print(f"  [ERR] {symbol}: {e}")

def main():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get all active symbols from instrument_master
    cur.execute("""
        SELECT symbol, instrument_key, instrument_id 
        FROM instrument_master 
        WHERE is_active = TRUE 
        ORDER BY symbol
    """)
    symbols = cur.fetchall()
    print(f"Starting catchup for {len(symbols)} symbols...")
    
    for i, (symbol, key, inst_id) in enumerate(symbols):
        print(f"[{i+1}/{len(symbols)}] Processing {symbol}...")
        catchup_symbol(conn, symbol, key, inst_id)
        # Rate limit safety
        time.sleep(0.5)

    conn.close()
    print("Universal Catchup Complete.")

if __name__ == "__main__":
    main()
