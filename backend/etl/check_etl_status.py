import psycopg2
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

def check_status():
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='admin',
            database='quantai'
        )
        cursor = conn.cursor()
        
        print("--- etl_job_status ---")
        cursor.execute("SELECT status, COUNT(*) FROM etl_job_status WHERE job_name = 'backfill_2022' GROUP BY status")
        rows = cursor.fetchall()
        if not rows:
            print("No entries in etl_job_status.")
        for row in rows:
            print(f"{row[0]}: {row[1]}")
            
        print("\n--- stock_candle_history ---")
        cursor.execute("SELECT COUNT(*) FROM stock_candle_history")
        count = cursor.fetchone()[0]
        print(f"Total rows: {count}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_status()
