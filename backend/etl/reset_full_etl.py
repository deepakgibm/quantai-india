import psycopg2

def reset_etl_jobs():
    try:
        conn = psycopg2.connect('postgresql://postgres:admin@localhost:5432/quantai')
        cur = conn.cursor()
        print("Resetting etl_job_status to PENDING for job 'backfill_2022'...")
        cur.execute("UPDATE etl_job_status SET status = 'PENDING' WHERE job_name = 'backfill_2022'")
        print(f"Success: Reset {cur.rowcount} symbols.")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error during reset: {e}")

if __name__ == "__main__":
    reset_etl_jobs()
