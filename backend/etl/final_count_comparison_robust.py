import psycopg2
import polars as pl
import os
from pathlib import Path

DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"
PARQUET_BASE_PATH = "data/parquet"

def get_fast_comparison():
    # 1. Get Row Count from PostgreSQL
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    print("Fetching total row count from PostgreSQL...")
    cur.execute("SELECT COUNT(*) FROM stock_candle_history")
    pg_count = cur.fetchone()[0]
    print(f"Total rows in PostgreSQL: {pg_count:,}")
    conn.close()

    # 2. Get Row Count from Parquet Files
    print(f"Scanning Parquet files in {PARQUET_BASE_PATH} (Robust Scan)...")
    
    try:
        base_p = Path(PARQUET_BASE_PATH)
        if not base_p.exists():
            print(f"Error: {base_p.absolute()} does not exist.")
            return

        all_files = list(base_p.rglob("*.parquet"))
        file_count = len(all_files)
        print(f"Total Parquet Files found: {file_count:,}")
        
        if file_count > 0:
            print("First 5 files found:")
            for f in all_files[:5]:
                print(f" - {f}")
            
            # Polars can scan a list of strings efficiently
            file_paths = [str(f) for f in all_files]
            
            print("Summing rows using Polars lazy scan...")
            total_parquet_rows = pl.scan_parquet(file_paths).select(pl.len()).collect().item()
        else:
            total_parquet_rows = 0
            
        print("\n--- FINAL COMPARISON ---")
        print(f"PostgreSQL Row Count: {pg_count:,}")
        print(f"Parquet Row Count:    {total_parquet_rows:,}")
        print(f"Row Difference:       {pg_count - total_parquet_rows:,}")
        print(f"Total Parquet Files:  {file_count}")
        print(f"Parquet File Location: {base_p.absolute()}")
        
    except Exception as e:
        print(f"Error in fast scan: {e}")

if __name__ == "__main__":
    get_fast_comparison()
