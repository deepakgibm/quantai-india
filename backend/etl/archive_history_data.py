import psycopg2
import sys

DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def archive_data():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        # 1. Create the archive table
        print("Creating stock_candle_archive table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stock_candle_archive (
                instrument_id bigint NOT NULL,
                timeframe smallint NOT NULL,
                candle_ts timestamp without time zone NOT NULL,
                open numeric,
                high numeric,
                low numeric,
                close numeric,
                volume bigint,
                CONSTRAINT stock_candle_archive_pkey PRIMARY KEY (instrument_id, timeframe, candle_ts)
            )
        """)
        
        # 2. Check current counts
        cur.execute("SELECT count(*) FROM stock_candle_history")
        history_count = cur.fetchone()[0]
        print(f"Current rows in stock_candle_history: {history_count}")
        
        if history_count == 0:
            print("No data in history table to archive. Exiting.")
            conn.close()
            return

        # 3. Transfer data
        print(f"Transferring {history_count} rows to stock_candle_archive...")
        cur.execute("""
            INSERT INTO stock_candle_archive 
            SELECT * FROM stock_candle_history
            ON CONFLICT DO NOTHING
        """)
        inserted_count = cur.rowcount
        print(f"Transferred {inserted_count} rows.")
        
        # 4. Verify archive count
        cur.execute("SELECT count(*) FROM stock_candle_archive")
        archive_total = cur.fetchone()[0]
        print(f"Total rows in stock_candle_archive: {archive_total}")
        
        # 5. Safety check: Verify counts match expectations
        # (This is a simplified check, assuming we want at least history_count successfully in archive)
        if archive_total >= history_count:
            print("Verification successful. Truncating stock_candle_history...")
            cur.execute("TRUNCATE TABLE stock_candle_history")
            print("stock_candle_history truncated.")
        else:
            print("ERROR: Archive count mismatch. Aborting truncation.")
            sys.exit(1)

        conn.commit()
        conn.close()
        print("Archiving Complete.")
        
    except Exception as e:
        print(f"Error during archiving: {e}")
        if conn: conn.rollback()
        sys.exit(1)

if __name__ == "__main__":
    archive_data()
