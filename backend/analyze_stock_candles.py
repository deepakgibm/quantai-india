import sys
import os
sys.path.append(os.getcwd())

from sqlalchemy import create_engine, text
from config import settings
import pandas as pd

def analyze_candles():
    print(f"Checking DB: {settings.SYNC_DATABASE_URL}")
    engine = create_engine(settings.SYNC_DATABASE_URL)
    
    with engine.connect() as conn:
        # 1. Unique Symbols Count
        res = conn.execute(text("SELECT count(distinct symbol) FROM stock_candles"))
        unique_symbols = res.scalar()
        print(f"\nUnique Symbols: {unique_symbols}")
        
        # 2. Row counts by Timeframe
        print("\n--- Rows by Timeframe ---")
        res = conn.execute(text("SELECT timeframe, count(*) FROM stock_candles GROUP BY timeframe"))
        for row in res:
            print(f"{row[0]}: {row[1]} rows")
            
        # 3. Distribution of '1d' data
        print("\n--- Distribution for timeframe='1d' ---")
        df = pd.read_sql(text("SELECT symbol, count(*) as count FROM stock_candles WHERE timeframe='1d' GROUP BY symbol"), conn)
        
        if df.empty:
            print("No data for 1d timeframe.")
        else:
            print(f"Min rows/symbol: {df['count'].min()}")
            print(f"Max rows/symbol: {df['count'].max()}")
            print(f"Avg rows/symbol: {df['count'].mean():.1f}")
            print(f"Symbols with > 20 rows: {len(df[df['count'] >= 20])}")
            
            print("\nTop 5 Symbols by row count:")
            print(df.sort_values('count', ascending=False).head(5))

        # 4. Check Date Range
        print("\n--- Date Range for '1d' ---")
        res = conn.execute(text("SELECT min(timestamp), max(timestamp) FROM stock_candles WHERE timeframe='1d'"))
        min_ts, max_ts = res.fetchone()
        print(f"Earliest: {min_ts}")
        print(f"Latest:   {max_ts}")

if __name__ == "__main__":
    analyze_candles()
