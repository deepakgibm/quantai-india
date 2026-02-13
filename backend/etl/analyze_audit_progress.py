import psycopg2

DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def analyze_audit_progress():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    # 1. Total symbols with at least one SUCCESS batch in audit
    cur.execute("""
        SELECT count(distinct symbol) 
        FROM parquet_load_audit 
        WHERE status = 'SUCCESS'
    """)
    total_success_in_audit = cur.fetchone()[0]
    
    # 2. Get the most recently updated symbols
    cur.execute("""
        SELECT symbol, MAX(last_updated) as last_val
        FROM parquet_load_audit
        WHERE status = 'SUCCESS'
        GROUP BY symbol
        ORDER BY last_val DESC
        LIMIT 20
    """)
    recent_symbols = cur.fetchall()
    
    print(f"Total Symbols in Audit (SUCCESS): {total_success_in_audit}")
    
    print("\nMost recently migrated symbols:")
    for row in recent_symbols:
        print(f"Symbol: {row[0]:<15} | Last Updated: {row[1]}")
        
    # 3. Get the alphabetical last symbol migrated
    cur.execute("""
        SELECT MAX(symbol) FROM parquet_load_audit WHERE status = 'SUCCESS'
    """)
    alpha_last = cur.fetchone()[0]
    print(f"\nAlphabetically last symbol in audit: {alpha_last}")
    
    conn.close()

if __name__ == "__main__":
    analyze_audit_progress()
