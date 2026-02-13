import psycopg2
from datetime import datetime

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': 'admin',
    'database': 'quantai'
}

def finalize_check():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    symbols = ['RELIANCE', 'NIFTY 50', 'TCS']
    print(f"--- FINAL VERIFICATION ({datetime.now()}) ---")
    
    for symbol in symbols:
        cur.execute("""
            SELECT instrument_id, instrument_key 
            FROM instrument_master 
            WHERE symbol = %s OR symbol = 'NSE_INDEX:' || %s
        """, (symbol, symbol))
        row = cur.fetchone()
        if not row:
            print(f"\n{symbol}: NOT FOUND in instrument_master")
            continue
        
        inst_id, key = row
        print(f"\n{symbol} (ID: {inst_id}, Key: {key}):")
        
        cur.execute("""
            SELECT timeframe, count(*), MAX(candle_ts) 
            FROM stock_candle_history 
            WHERE instrument_id = %s 
            GROUP BY timeframe 
            ORDER BY timeframe
        """, (inst_id,))
        stats = cur.fetchall()
        for tf, count, max_ts in stats:
            print(f"  TF: {tf:6} | Count: {count:10} | Latest: {max_ts}")
            
    conn.close()

if __name__ == "__main__":
    finalize_check()
