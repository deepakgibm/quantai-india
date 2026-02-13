import psycopg2
from datetime import datetime

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': 'admin',
    'database': 'quantai'
}

def verify_today():
    today = '2026-02-06'
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Check Daily
    cur.execute("SELECT count(DISTINCT instrument_id) FROM stock_candle_history WHERE candle_ts::date = %s AND timeframe = 1440", (today,))
    daily_count = cur.fetchone()[0]
    
    # Check Intraday (1m)
    cur.execute("SELECT count(DISTINCT instrument_id) FROM stock_candle_history WHERE candle_ts::date = %s AND timeframe = 1", (today,))
    minute_count = cur.fetchone()[0]
    
    # Total distinct instruments that have ANY data for today (could be resampled too)
    cur.execute("SELECT count(DISTINCT instrument_id) FROM stock_candle_history WHERE candle_ts::date = %s", (today,))
    total_distinct_today = cur.fetchone()[0]
    
    # Compare with ETL status
    cur.execute("SELECT count(*) FROM etl_job_status WHERE job_name = 'backfill_2022' AND status = 'COMPLETED'")
    completed_in_job = cur.fetchone()[0]
    
    print(f"=== Verification for {today} ===")
    print(f"Instruments with Daily (1D) data: {daily_count}")
    print(f"Instruments with 1-Minute (1m) data: {minute_count}")
    print(f"Total distinct instruments with ANY data for today: {total_distinct_today}")
    print(f"Total 'COMPLETED' symbols in ETL job status: {completed_in_job}")
    
    if daily_count == 0 and completed_in_job > 0:
        print("\n[WARNING] ETL job marked symbols as COMPLETED, but no Daily candles found for today.")
        print("Checking sample candle_ts range...")
        cur.execute("SELECT MAX(candle_ts) FROM stock_candle_history")
        max_ts = cur.fetchone()[0]
        print(f"Overall Max Timestamp in history: {max_ts}")
    
    conn.close()

if __name__ == "__main__":
    verify_today()
