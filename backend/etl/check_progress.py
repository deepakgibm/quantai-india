import psycopg2
from datetime import datetime, timedelta

DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def check_progress():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    # 1. Total symbols with at least one SUCCESS batch
    cur.execute("SELECT count(distinct symbol) FROM parquet_load_audit WHERE status = 'SUCCESS'")
    success_count = cur.fetchone()[0]
    
    # 2. Most recent 5 successful batches across all symbols
    cur.execute("""
        SELECT symbol, timeframe, year, month, last_updated 
        FROM parquet_load_audit 
        WHERE status = 'SUCCESS'
        ORDER BY last_updated DESC 
        LIMIT 5
    """)
    recent = cur.fetchall()
    
    # 3. Count of batches successful in the last 10 minutes
    ten_mins_ago = datetime.now() - timedelta(minutes=10)
    cur.execute("SELECT count(*) FROM parquet_load_audit WHERE status = 'SUCCESS' AND last_updated > %s", (ten_mins_ago,))
    recent_success_count = cur.fetchone()[0]
    
    print(f"Total Successful Symbols: {success_count}")
    print(f"Successful batches in last 10 mins: {recent_success_count}")
    print("\nMost Recent Successful Batches:")
    for r in recent:
        print(f" - {r[0]} | TF: {r[1]} | {r[2]}-{r[3]:02d} | Updated: {r[4]}")
        
    conn.close()

if __name__ == "__main__":
    check_progress()
