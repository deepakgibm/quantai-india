import psycopg2

DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def check_pending_optimized():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    # 1. Total symbols in instrument_master
    cur.execute("SELECT count(*) FROM instrument_master")
    total_master = cur.fetchone()[0]
    
    # 2. Total symbols in instrument_master with history
    cur.execute("""
        SELECT count(distinct instrument_id)
        FROM stock_candle_history
    """)
    symbols_with_history = cur.fetchone()[0]
    
    # 3. Migrated symbols in audit
    cur.execute("SELECT count(distinct symbol) FROM parquet_load_audit WHERE status = 'SUCCESS'")
    migrated_symbols = cur.fetchone()[0]
    
    # 4. Find symbols that have history but are not in audit
    cur.execute("""
        WITH hist_symbols AS (
            SELECT DISTINCT m.symbol
            FROM stock_candle_history h
            JOIN instrument_master m ON h.instrument_id = m.instrument_id
        ),
        audit_symbols AS (
            SELECT DISTINCT symbol FROM parquet_load_audit WHERE status = 'SUCCESS'
        )
        SELECT symbol FROM hist_symbols
        EXCEPT
        SELECT symbol FROM audit_symbols
    """)
    unprocessed = [r[0] for r in cur.fetchall()]
    
    print(f"Total Symbols in instrument_master: {total_master}")
    print(f"Total Symbols with History in DB: {symbols_with_history}")
    print(f"Total Symbols fully/partially migrated: {migrated_symbols}")
    print(f"Total Symbols with history but ZERO batches in audit: {len(unprocessed)}")
    if unprocessed:
        print(f"Unprocessed (First 20): {unprocessed[:20]}")
    
    conn.close()

if __name__ == "__main__":
    check_pending_optimized()
