import psycopg2

DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def check_db_meta():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    with open("backend/etl/db_meta_info.txt", "w", encoding="utf-8") as f:
        f.write("Checking indexes on stock_candle_history...\n")
        cur.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'stock_candle_history'
        """)
        for row in cur.fetchall():
            f.write("-" * 20 + "\n")
            f.write(f"Index: {row[0]}\n")
            f.write(f"Def: {row[1]}\n")
            
        f.write("\n" + "=" * 40 + "\n")
        f.write("Checking parquet_load_audit schema...\n")
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'parquet_load_audit'
            ORDER BY ordinal_position
        """)
        for row in cur.fetchall():
            f.write(f"Col: {row[0]:<20} | Type: {row[1]}\n")
            
    print("Metadata written to backend/etl/db_meta_info.txt")
        
    conn.close()

if __name__ == "__main__":
    check_db_meta()
