import polars as pl
from pathlib import Path

def final_global_check():
    symbols_to_check = ["INFY", "TCS", "HDFCBANK", "RELIANCE"]
    for symbol in symbols_to_check:
        base_dir = Path(f"data/parquet/symbol={symbol}")
        print(f"\n--- Checking {symbol} ---")
        try:
            # Check 1m
            path_1m = base_dir / "timeframe=1/year=2026/month=02/data_2026_02.parquet"
            if path_1m.exists():
                df_1m = pl.read_parquet(path_1m)
                print(f"  1m Max Parquet TS: {df_1m['candle_ts'].max()}")
            else:
                print(f"  1m file missing at {path_1m}")

            # Check 1d
            path_1d = base_dir / "timeframe=1440/year=2026/month=02/data_2026_02.parquet"
            if path_1d.exists():
                df_1d = pl.read_parquet(path_1d)
                print(f"  1d Max Parquet TS: {df_1d['candle_ts'].max()}")
            else:
                print(f"  1d file missing at {path_1d}")
        except Exception as e:
            print(f"  Error checking {symbol}: {e}")

if __name__ == "__main__":
    final_global_check()
