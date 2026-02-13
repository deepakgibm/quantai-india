import psycopg2

def check_skip_reasons():
    try:
        conn = psycopg2.connect('postgresql://postgres:admin@localhost:5432/quantai')
        cur = conn.cursor()
        cur.execute("SELECT error_msg, count(*) FROM etl_job_status WHERE job_name = 'backfill_2022' AND status = 'SKIPPED' GROUP BY error_msg")
        rows = cur.fetchall()
        print("--- SKIP REASONS ---")
        for msg, count in rows:
            print(f"Count: {count} | Reason: {msg}")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_skip_reasons()
