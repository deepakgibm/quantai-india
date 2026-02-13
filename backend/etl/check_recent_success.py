import psycopg2

DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def check_recent_success():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    print("Listing most recent successful symbols in audit table...")
    cur.execute("""
        SELECT symbol, timeframe, year, month, last_updated 
        FROM parquet_load_audit 
        WHERE status = 'SUCCESS'
        ORDER BY last_updated DESC 
        LIMIT 20
    """)
    rows = cur.fetchall()
    
    for r in rows:
        print(f" - {r[0]} | TF: {r[1]} | {r[2]}-{r[3]:02d} | Updated: {r[4]}")
        
    conn.close()

if __name__ == "__main__":
    check_recent_success()
