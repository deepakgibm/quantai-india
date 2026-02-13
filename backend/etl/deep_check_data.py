import psycopg2

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': 'admin',
    'database': 'quantai'
}

def deep_check():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    symbols = ['RELIANCE', 'TCS']
    
    for symbol in symbols:
        print(f"\n--- Deep Check: {symbol} ---")
        cur.execute("SELECT instrument_id, instrument_key FROM instrument_master WHERE symbol = %s", (symbol,))
        row = cur.fetchone()
        if not row:
            print(f"  FAILED: Symbol {symbol} not found in instrument_master")
            continue
        
        inst_id, inst_key = row
        print(f"  Instrument ID: {inst_id}, Key: {inst_key}")
        
        # Check counts per timeframe
        cur.execute("""
            SELECT timeframe, count(*), MAX(candle_ts) 
            FROM stock_candle_history 
            WHERE instrument_id = %s 
            GROUP BY timeframe 
            ORDER BY timeframe
        """, (inst_id,))
        rows = cur.fetchall()
        
        if not rows:
            print("  NO CANDLES FOUND in stock_candle_history")
        else:
            for tf, count, max_ts in rows:
                print(f"  TF: {tf}m | Count: {count} | Latest: {max_ts}")
                
    conn.close()

if __name__ == "__main__":
    deep_check()
