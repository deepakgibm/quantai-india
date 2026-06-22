import duckdb
import os
import time

conn = duckdb.connect(':memory:')
base_path = '/data/feature_store'

print(f"Benchmarking path: {base_path}")

# 1. Benchmark os.walk
start = time.time()
files = []
for root, dirs, fnames in os.walk(base_path):
    for f in fnames:
        if f.endswith('.parquet'):
            files.append(os.path.join(root, f))
print(f"os.walk found {len(files)} files in {time.time() - start:.4f}s")

if not files:
    print("No files found!")
    exit(1)

# 2. Benchmark DuckDB read_parquet with specific glob
pattern = os.path.join(base_path, "feature_version=*", "timeframe=*", "symbol=*", "year=*", "*.parquet")
print(f"Benchmarking DuckDB with pattern: {pattern}")
start = time.time()
try:
    conn.execute(f"CREATE OR REPLACE VIEW test_view AS SELECT * FROM read_parquet('{pattern}', hive_partitioning=1)")
    count = conn.execute("SELECT count(*) FROM test_view").fetchone()[0]
    print(f"DuckDB View created and counted {count} rows in {time.time() - start:.4f}s")
except Exception as e:
    print(f"DuckDB Pattern Error: {e}")

# 3. Benchmark DuckDB read_parquet with recursive glob
pattern_rec = os.path.join(base_path, "**", "*.parquet")
print(f"Benchmarking DuckDB with recursive pattern: {pattern_rec}")
start = time.time()
try:
    conn.execute(f"CREATE OR REPLACE VIEW test_view_rec AS SELECT * FROM read_parquet('{pattern_rec}', hive_partitioning=1)")
    count = conn.execute("SELECT count(*) FROM test_view_rec").fetchone()[0]
    print(f"DuckDB Recursive View created and counted {count} rows in {time.time() - start:.4f}s")
except Exception as e:
    print(f"DuckDB Recursive Error: {e}")

# 4. Benchmark single file
start = time.time()
conn.execute(f"SELECT count(*) FROM read_parquet('{files[0]}')")
print(f"DuckDB single file read in {time.time() - start:.4f}s")
