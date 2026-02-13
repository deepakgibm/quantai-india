import polars as pl
from pathlib import Path

def final_parquet_check():
    base_dir = Path("data/parquet/symbol=RELIANCE")
    
    # Check 1d
    df_1d = pl.read_parquet(base_dir / "timeframe=1440/year=2026/month=02/data_2026_02.parquet")
    print(f"RELIANCE Daily (1440) Max Parquet TS: {df_1d['candle_ts'].max()}")
    
    # Check 1m
    df_1m = pl.read_parquet(base_dir / "timeframe=1/year=2026/month=02/data_2026_02.parquet")
    print(f"RELIANCE 1m Max Parquet TS: {df_1m['candle_ts'].max()}")
    
    # Check 15m
    df_15m = pl.read_parquet(base_dir / "timeframe=15/year=2026/month=02/data_2026_02.parquet")
    print(f"RELIANCE 15m Max Parquet TS: {df_15m['candle_ts'].max()}")

if __name__ == "__main__":
    final_parquet_check()
