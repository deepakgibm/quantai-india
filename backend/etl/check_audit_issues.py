import psycopg2

DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def check_audit_issues():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    print("Checking for IN_PROGRESS or FAILED batches in parquet_load_audit...")
    cur.execute("""
        SELECT symbol, timeframe, year, month, status, error_message
        FROM parquet_load_audit
        WHERE status != 'SUCCESS'
    """)
    rows = cur.fetchall()
    
    if not rows:
        print("No pending or failed batches found in audit table.")
    else:
        print(f"Found {len(rows)} problematic batches:")
        for row in rows:
            print(f"Symbol: {row[0]}, TF: {row[1]}, Date: {row[2]}-{row[3]:02d}, Status: {row[4]}, Error: {row[5]}")
            
    conn.close()

if __name__ == "__main__":
    check_audit_issues()
