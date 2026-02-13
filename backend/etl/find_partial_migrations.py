import psycopg2

DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def find_partial_migrations():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    print("Finding symbols with partial migrations (gaps in months)...")
    # This query finds symbols that have some SUCCESS months but not all.
    # It's hard to define "all" without knowing the full range, but we can look for symbols
    # that have multiple entries in audit and see if they look incomplete.
    
    # Alternatively, let's just see symbols that were updated very recently but didn't reach the end.
    cur.execute("""
        SELECT symbol, timeframe, count(*) as successful_months, min(month) as min_m, max(month) as max_m, min(year) as min_y, max(year) as max_y
        FROM parquet_load_audit
        WHERE status = 'SUCCESS'
        GROUP BY symbol, timeframe
        ORDER BY max(last_updated) DESC
        LIMIT 20
    """)
    rows = cur.fetchall()
    for row in rows:
        print(f"Symbol: {row[0]:<15} | TF: {row[1]:<3} | Months: {row[2]:<3} | Range: {row[5]}-{row[3]:02d} to {row[6]}-{row[4]:02d}")
        
    conn.close()

if __name__ == "__main__":
    find_partial_migrations()
