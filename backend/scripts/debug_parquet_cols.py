import duckdb
import pandas as pd

conn = duckdb.connect(':memory:')
parquet_file = '/data/feature_store/feature_version=v1/timeframe=5m/symbol=ASIANPAINT/year=2026/month=1.parquet'

print(f"Checking file: {parquet_file}")
try:
    # Check with pandas first
    df_pd = pd.read_parquet(parquet_file)
    print(f"Pandas columns: {df_pd.columns.tolist()}")
    
    # Check with DuckDB
    df_duck = conn.execute(f"SELECT * FROM read_parquet('{parquet_file}')").df()
    print(f"DuckDB columns: {df_duck.columns.tolist()}")
    
    # Check with DuckDB View logic
    conn.execute(f"CREATE VIEW test_view AS SELECT * FROM read_parquet('{parquet_file}')")
    df_view = conn.execute("SELECT * FROM test_view").df()
    print(f"DuckDB View columns: {df_view.columns.tolist()}")

except Exception as e:
    print(f"Error: {e}")
