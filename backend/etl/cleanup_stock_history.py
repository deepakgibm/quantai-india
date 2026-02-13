import psycopg2
import sys
from datetime import datetime, timedelta

DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def cleanup_data(days=45):
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        # Calculate threshold date
        threshold_date = datetime.now() - timedelta(days=days)
        threshold_str = threshold_date.strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"--- Cleanup Configuration ---")
        print(f"Retention Period: {days} days")
        print(f"Threshold Date: {threshold_str}")
        print(f"-----------------------------")
        
        # 1. Count rows to be deleted
        cur.execute("SELECT count(*) FROM stock_candle_history WHERE candle_ts < %s", (threshold_str,))
        count_to_delete = cur.fetchone()[0]
        
        if count_to_delete == 0:
            print("No data older than threshold found. Cleanup not required.")
            conn.close()
            return

        print(f"Found {count_to_delete} rows older than {threshold_str}.")
        
        # 2. Execute deletion
        print("Executing deletion...")
        cur.execute("DELETE FROM stock_candle WHERE candle_ts < %s", (threshold_str,))
        rows_deleted = cur.rowcount
        
        # 3. Final count
        cur.execute("SELECT count(*) FROM stock_candle_history")
        remaining_count = cur.fetchone()[0]
        
        conn.commit()
        print(f"Cleanup Successful:")
        print(f"  Rows Deleted: {rows_deleted}")
        print(f"  Rows Remaining: {remaining_count}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
        if 'conn' in locals() and conn: conn.rollback()
        sys.exit(1)

if __name__ == "__main__":
    days = 45
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            pass
    cleanup_data(days)
