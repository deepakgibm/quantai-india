import psycopg2
import polars as pl
import os
import glob
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
    print(f"Scanning Parquet files in {PARQUET_BASE_PATH} (Parallel Fast Scan)...")
    
    # Use glob to find all parquet files
    # The pattern is data/parquet/SYMBOL/TIMEFRAME/YEAR/data_YEAR_MONTH.parquet
    pattern = os.path.join(PARQUET_BASE_PATH, "*", "*", "*", "*.parquet")
    
    try:
        # Polars scan_parquet can take a glob pattern or a list of files
        # Let's use glob to get the list and then scan_parquet for speed
        all_files = glob.glob(pattern)
        file_count = len(all_files)
        print(f"Total Parquet Files found: {file_count:,}")
        
        if file_count > 0:
            # Polars can scan a list of files efficiently in parallel
            df = pl.scan_parquet(all_files)
            total_parquet_rows = df.select(pl.len()).collect().item()
        else:
            total_parquet_rows = 0
            
        print("\n--- FINAL COMPARISON ---")
        print(f"PostgreSQL Row Count: {pg_count:,}")
        print(f"Parquet Row Count:    {total_parquet_rows:,}")
        print(f"Row Difference:       {pg_count - total_parquet_rows:,}")
        print(f"Total Parquet Files:  {file_count}")
        print(f"Parquet File Location: {os.path.abspath(PARQUET_BASE_PATH)}")
        
    except Exception as e:
        print(f"Error in fast scan: {e}")

if __name__ == "__main__":
    get_fast_comparison()
