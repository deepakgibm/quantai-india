import psycopg2

DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def get_first_missing():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    query = """
        SELECT DISTINCT m.symbol 
        FROM instrument_master m 
        JOIN stock_candle_history h ON m.instrument_id = h.instrument_id 
        LEFT JOIN parquet_load_audit a ON m.symbol = a.symbol 
        WHERE a.symbol IS NULL 
        ORDER BY m.symbol 
        LIMIT 1
    """
    cur.execute(query)
    row = cur.fetchone()
    if row:
        print(f"FIRST_MISSING: {row[0]}")
    else:
        print("FIRST_MISSING: NONE")
        
    conn.close()

if __name__ == "__main__":
    get_first_missing()
