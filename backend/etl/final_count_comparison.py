import psycopg2
import polars as pl
import os
from pathlib import Path

DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"
PARQUET_BASE_PATH = "data/parquet"

def get_final_comparison():
    # 1. Get Row Count from PostgreSQL
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    print("Fetching total row count from PostgreSQL...")
    cur.execute("SELECT COUNT(*) FROM stock_candle_history")
    pg_count = cur.fetchone()[0]
    print(f"Total rows in PostgreSQL: {pg_count:,}")
    conn.close()

    # 2. Get Row Count from Parquet Files
    print(f"Scanning Parquet files in {PARQUET_BASE_PATH}...")
    total_parquet_rows = 0
    file_count = 0
    
    if os.path.exists(PARQUET_BASE_PATH):
        try:
            base_p = Path(PARQUET_BASE_PATH)
            for file_p in base_p.rglob("*.parquet"):
                file_count += 1
                try:
                    # Use scan_parquet for efficiency
                    total_parquet_rows += pl.scan_parquet(file_p).select(pl.count()).collect().item()
                except Exception as e:
                    print(f"Error reading {file_p}: {e}")
                
                if file_count % 10000 == 0:
                    print(f"Processed {file_count} files...")
        except Exception as e:
            print(f"Error scanning parquet files: {e}")
    else:
        print(f"Warning: Parquet base path {PARQUET_BASE_PATH} does not exist.")

    print("\n--- FINAL COMPARISON ---")
    print(f"PostgreSQL Row Count: {pg_count:,}")
    print(f"Parquet Row Count:    {total_parquet_rows:,}")
    print(f"Row Difference:       {pg_count - total_parquet_rows:,}")
    print(f"Total Parquet Files:  {file_count}")
    print(f"Parquet File Location: {os.path.abspath(PARQUET_BASE_PATH)}")

if __name__ == "__main__":
    get_final_comparison()
