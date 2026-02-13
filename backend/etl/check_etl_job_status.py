import psycopg2

DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def check_etl_job_status():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    print("Checking etl_job_status for job 'backfill_2022'...")
    cur.execute("""
        SELECT symbol, status, error_msg 
        FROM etl_job_status 
        WHERE job_name = 'backfill_2022' AND status != 'COMPLETED'
    """)
    rows = cur.fetchall()
    
    if not rows:
        print("No pending or failed symbols in etl_job_status for 'backfill_2022'.")
    else:
        print(f"Found {len(rows)} problematic symbols in etl_job_status:")
        for row in rows:
            print(f"Symbol: {row[0]}, Status: {row[1]}, Error: {row[2]}")
            
    conn.close()

if __name__ == "__main__":
    check_etl_job_status()
