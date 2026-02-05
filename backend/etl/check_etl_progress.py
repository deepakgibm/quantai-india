import psycopg2
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

def check_progress():
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='admin',
            database='quantai'
        )
        cursor = conn.cursor()
        
        print("--- ETL Job Status (backfill_2022) ---")
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM etl_job_status 
            WHERE job_name = 'backfill_2022' 
            GROUP BY status
        """)
        rows = cursor.fetchall()
        for row in rows:
            print(f"{row[0]}: {row[1]}")
            
        print("\n--- Recent Activity (Last 5) ---")
        cursor.execute("""
            SELECT symbol, status, last_updated, error_msg 
            FROM etl_job_status 
            WHERE job_name = 'backfill_2022'
            ORDER BY last_updated DESC 
            LIMIT 5
        """)
        recent = cursor.fetchall()
        for r in recent:
            err = f" | {r[3]}" if r[3] else ""
            print(f"{r[0]}: {r[1]} @ {r[2]}{err}")

        print("\n--- stock_candle_history Row Count ---")
        cursor.execute("SELECT COUNT(*) FROM stock_candle_history")
        count = cursor.fetchone()[0]
        print(f"Total Rows: {count:,}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_progress()
