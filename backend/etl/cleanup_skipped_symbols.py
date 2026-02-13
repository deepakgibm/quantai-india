import psycopg2

def cleanup_skipped():
    try:
        conn = psycopg2.connect('postgresql://postgres:admin@localhost:5432/quantai')
        cur = conn.cursor()
        
        # 1. Get symbols
        cur.execute("SELECT symbol FROM etl_job_status WHERE job_name = 'backfill_2022' AND status = 'SKIPPED'")
        symbols = [r[0] for r in cur.fetchall()]
        print(f"Found {len(symbols)} skipped symbols.")
        print(f"SYMBOLS: {symbols}")
        
        if symbols:
            # 2. Delete from etl_job_status
            print("Deleting from etl_job_status...")
            cur.execute("DELETE FROM etl_job_status WHERE job_name = 'backfill_2022' AND status = 'SKIPPED'")
            print(f"Deleted {cur.rowcount} rows.")
            
            # 3. Mark as inactive in instrument_master (if they exist)
            print("Marking as inactive in instrument_master...")
            cur.execute("UPDATE instrument_master SET is_active = FALSE WHERE symbol = ANY(%s)", (symbols,))
            print(f"Updated {cur.rowcount} rows in instrument_master.")
            
        conn.commit()
        conn.close()
        return symbols
    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    cleanup_skipped()
