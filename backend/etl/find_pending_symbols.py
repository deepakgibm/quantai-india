import psycopg2

DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def find_pending_symbols():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    print("Finding symbols with history that are missing from audit...")
    # This query finds symbols in IM that have at least one record in history but NO records in audit
    query = """
        SELECT DISTINCT m.symbol
        FROM instrument_master m
        WHERE EXISTS (
            SELECT 1 FROM stock_candle_history h 
            WHERE h.instrument_id = m.instrument_id 
            LIMIT 1
        )
        AND NOT EXISTS (
            SELECT 1 FROM parquet_load_audit a 
            WHERE a.symbol = m.symbol
        )
    """
    cur.execute(query)
    missing_symbols = [r[0] for r in cur.fetchall()]
    
    print(f"COUNT: {len(missing_symbols)}")
    for s in missing_symbols:
        print(f"SYMBOL: {s}")
    
    conn.close()

if __name__ == "__main__":
    find_pending_symbols()
