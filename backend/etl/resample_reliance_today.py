import psycopg2
import pandas as pd
from datetime import datetime

DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def resample_and_insert(conn, instrument_id, df_1m, target_tf_str, target_mins):
    """Resample 1m data and insert into stock_candle_history"""
    if df_1m.empty: return
    try:
        resample_df = df_1m.copy()
        resample_df.set_index('candle_ts', inplace=True)
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
            INSERT INTO stock_candle_history (instrument_id, candle_ts, open, high, low, close, volume, timeframe)
            VALUES {args_str}
            ON CONFLICT (instrument_id, timeframe, candle_ts) DO NOTHING
        """)
        conn.commit()
        print(f"Resampled and inserted {len(records)} rows for {target_tf_str} ({target_mins}m)")
    except Exception as e:
        print(f"Error resampling {target_tf_str}: {e}")

def process_reliance_resample():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    # Get RELIANCE ID
    cur.execute("SELECT instrument_id FROM instrument_master WHERE symbol = 'RELIANCE' LIMIT 1")
    inst_id = cur.fetchone()[0]
    
    # Fetch 1m data for today
    query = f"SELECT candle_ts, open, high, low, close, volume FROM stock_candle_history WHERE instrument_id = {inst_id} AND timeframe = 1 AND candle_ts >= '2026-02-09' ORDER BY candle_ts"
    df_1m = pd.read_sql(query, conn)
    
    if df_1m.empty:
        print("No 1m data found for Feb 9th to resample.")
        conn.close()
        return

    print(f"Resampling {len(df_1m)} 1m rows for RELIANCE...")
    
    # Resample to: 3m, 5m, 15m, 30m, 1H
    resample_and_insert(conn, inst_id, df_1m, '3T', 3)
    resample_and_insert(conn, inst_id, df_1m, '5T', 5)
    resample_and_insert(conn, inst_id, df_1m, '15T', 15)
    resample_and_insert(conn, inst_id, df_1m, '30T', 30)
    resample_and_insert(conn, inst_id, df_1m, '1H', 60)
    
    conn.close()

if __name__ == "__main__":
    process_reliance_resample()
