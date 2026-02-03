
import sys
import os
import psycopg2
from pathlib import Path

# Add project root to path
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
        
        print("Checking etl_job_status table...")
        cursor.execute("SELECT job_name, status, count(*) FROM etl_job_status GROUP BY job_name, status;")
        rows = cursor.fetchall()
        print("\nJob Status Summary:")
        for row in rows:
            print(f"Job: {row[0]}, Status: {row[1]}, Count: {row[2]}")

        print("\nChecking recent failures:")
        cursor.execute("SELECT job_name, symbol, error_msg FROM etl_job_status WHERE status = 'FAILED' ORDER BY last_updated DESC LIMIT 5;")
        failures = cursor.fetchall()
        if not failures:
            print("No recent failures found.")
        for row in failures:
            print(f"Job: {row[0]}, Symbol: {row[1]}, Error: {row[2]}")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error checking status: {e}")

if __name__ == "__main__":
    check_status()
