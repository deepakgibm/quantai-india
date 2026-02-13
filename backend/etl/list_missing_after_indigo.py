import psycopg2

DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def list_missing_after_indigo():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    print("Listing symbols missing from audit alphabetically after INDIGO...")
    query = """
        SELECT DISTINCT m.symbol 
        FROM instrument_master m 
        JOIN stock_candle_history h ON m.instrument_id = h.instrument_id 
        WHERE m.symbol > 'INDIGO' 
        ORDER BY m.symbol
    """
    cur.execute(query)
    symbols = [r[0] for r in cur.fetchall()]
    
    if not symbols:
        print("No symbols found after INDIGO with history.")
    else:
        print(f"Found {len(symbols)} symbols after INDIGO:")
        for s in symbols:
            print(f" - {s}")
            
    conn.close()

if __name__ == "__main__":
    list_missing_after_indigo()
