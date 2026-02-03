
import sys
import psycopg2
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

def reset_jobs():
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='admin',
            database='quantai'
        )
        cursor = conn.cursor()
        
        print("Resetting stuck 'PROCESSING' jobs to 'PENDING' for 'backfill_2022'...")
        cursor.execute("""
            UPDATE etl_job_status 
            SET status = 'PENDING', error_msg = 'Reset by manual intervention'
            WHERE job_name = 'backfill_2022' AND status = 'PROCESSING';
        """)
        updated_rows = cursor.rowcount
        conn.commit()
        print(f"Reset {updated_rows} jobs.")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error resetting jobs: {e}")

if __name__ == "__main__":
    reset_jobs()
