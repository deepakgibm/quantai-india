import psycopg2

def compare_schemas():
    DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        # Get columns for stock_candle
        cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'stock_candle' ORDER BY column_name")
        cols_candle = dict(cur.fetchall())
        
        # Get columns for stock_candle_history
        cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'stock_candle_history' ORDER BY column_name")
        cols_history = dict(cur.fetchall())
        
        print("Schema Comparison Report")
        print("========================")
        print(f"{'Column Name':<20} | {'stock_candle':<20} | {'stock_candle_history':<20}")
        print("-" * 65)
        
        all_cols = sorted(set(cols_candle.keys()) | set(cols_history.keys()))
        for col in all_cols:
            t1 = cols_candle.get(col, "MISSING")
            t2 = cols_history.get(col, "MISSING")
            match = "v" if t1 == t2 else "x"
            print(f"{col:<20} | {t1:<20} | {t2:<20} {match}")
            
        cur.close()
        conn.close()
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    compare_schemas()
