import psycopg2

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': 'admin',
    'database': 'quantai'
}

def check_final_status():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT status, count(*) FROM etl_job_status WHERE job_name = 'backfill_2022' GROUP BY status")
    rows = cur.fetchall()
    print("--- Final ETL Execution Summary ---")
    total = 0
    for status, count in rows:
        print(f" {status}: {count}")
        total += count
    print(f" Total Symbols: {total}")
    conn.close()

if __name__ == "__main__":
    check_final_status()
