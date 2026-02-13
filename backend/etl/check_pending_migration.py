import psycopg2

DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def check_pending():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    # 1. Total symbols in instrument_master that have history
    cur.execute("""
        SELECT count(distinct m.symbol)
        FROM instrument_master m
        JOIN stock_candle_history h ON m.instrument_id = h.instrument_id
    """)
    total_symbols = cur.fetchone()[0]
    
    # 2. Symbols already in audit with SUCCESS status (at least one batch)
    cur.execute("""
        SELECT count(distinct symbol) 
        FROM parquet_load_audit 
        WHERE status = 'SUCCESS'
    """)
    migrated_symbols = cur.fetchone()[0]
    
    # 3. Symbols not in audit at all
    cur.execute("""
        SELECT DISTINCT m.symbol
        FROM instrument_master m
        JOIN stock_candle_history h ON m.instrument_id = h.instrument_id
        LEFT JOIN parquet_load_audit a ON m.symbol = a.symbol
        WHERE a.symbol IS NULL
    """)
    unprocessed_symbols = [r[0] for r in cur.fetchall()]
    
    # 4. Batches in audit that are NOT SUCCESS
    cur.execute("""
        SELECT status, count(*) 
        FROM parquet_load_audit 
        WHERE status != 'SUCCESS'
        GROUP BY status
    """)
    pending_batches = cur.fetchall()
    
    print(f"Total Symbols with History: {total_symbols}")
    print(f"Symbols with at least one Successful Batch: {migrated_symbols}")
    print(f"Symbols with NO batches in audit: {len(unprocessed_symbols)}")
    if unprocessed_symbols:
        print(f"Unprocessed Symbols (First 10): {unprocessed_symbols[:10]}")
    
    print("\nPending/Failed Batches in Audit:")
    for status, count in pending_batches:
        print(f" {status}: {count}")
    
    conn.close()

if __name__ == "__main__":
    check_pending()
