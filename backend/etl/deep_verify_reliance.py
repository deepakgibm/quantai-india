import psycopg2
from datetime import datetime

def verify_reliance_data():
    try:
        conn = psycopg2.connect('postgresql://postgres:admin@localhost:5432/quantai')
        cur = conn.cursor()
        
        # Get instrument_id
        cur.execute("SELECT instrument_id FROM instrument_master WHERE symbol = 'RELIANCE' LIMIT 1")
        inst_id = cur.fetchone()[0]
        
        print(f"RELIANCE Instrument ID: {inst_id}")
        
        # Check specific dates
        cur.execute("""
            SELECT candle_ts::date, count(*) 
            FROM stock_candle_history 
            WHERE instrument_id = %s AND candle_ts >= '2026-02-06'
            GROUP BY candle_ts::date
            ORDER BY candle_ts::date
        """, (inst_id,))
        
        rows = cur.fetchall()
        print("\n--- Rows per Day (DB) ---")
        for d, count in rows:
            print(f"Date: {d} | Row Count: {count}")
            
        # Check max timestamp for 1m specifically
        cur.execute("""
            SELECT MAX(candle_ts) 
            FROM stock_candle_history 
            WHERE instrument_id = %s AND timeframe = 1
        """, (inst_id,))
        max_ts_1m = cur.fetchone()[0]
        print(f"\nMax 1m Timestamp: {max_ts_1m}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_reliance_data()
