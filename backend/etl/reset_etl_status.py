import psycopg2
import sys
from pathlib import Path

def reset_stuck_jobs():
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='admin',
            database='quantai'
        )
        cursor = conn.cursor()
        
        cursor.execute("UPDATE etl_job_status SET status = 'PENDING' WHERE job_name = 'backfill_2022' AND status = 'PROCESSING'")
        count = cursor.rowcount
        conn.commit()
        print(f"Reset {count} processing jobs to PENDING.")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    reset_stuck_jobs()
