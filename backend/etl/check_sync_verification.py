import psycopg2

def check_reliance():
    try:
        conn = psycopg2.connect('postgresql://postgres:admin@localhost:5432/quantai')
        cur = conn.cursor()
        
        # Get instrument_id
        cur.execute("SELECT instrument_id FROM instrument_master WHERE symbol = 'RELIANCE' LIMIT 1")
        inst_id = cur.fetchone()[0]
        
        # Get Max candle_ts from DB
        cur.execute("SELECT timeframe, MAX(candle_ts) FROM stock_candle_history WHERE instrument_id = %s GROUP BY timeframe", (inst_id,))
        db_rows = cur.fetchall()
        print("--- DB Timestamps (RELIANCE) ---")
        for tf, ts in db_rows:
            print(f"TF: {tf} | Max TS: {ts}")
            
        # Get Max candle_ts from Parquet Audit
        cur.execute("SELECT timeframe, MAX(max_ts_parquet) FROM parquet_load_audit WHERE symbol = 'RELIANCE' GROUP BY timeframe")
        audit_rows = cur.fetchall()
        print("\n--- Parquet Audit Timestamps (RELIANCE) ---")
        for tf, ts in audit_rows:
            print(f"TF: {tf} | Max Parquet TS: {ts}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_reliance()
