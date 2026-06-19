import sys
import os
import pandas as pd
import numpy as np

# Add backend directory to sys.path
sys.path.append(r"c:\Users\Deepak Kumar\Downloads\quantai-india\backend")
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:admin@localhost:5432/quantai"

from services.momentum_scanner import MomentumScanner

def get_bucket(score):
    if score >= 80:
        return "STRONG_BULLISH"
    elif score >= 60:
        return "MODERATE_BULLISH"
    elif score >= 40:
        return "NEUTRAL"
    elif score >= 30:
        return "MODERATE_BEARISH"
    else:
        return "STRONG_BEARISH"

def main():
    scanner = MomentumScanner()
    df = scanner._get_bulk_ohlcv_df()
    if df.empty:
        print("No OHLCV data found!")
        return
    df = scanner._calculate_indicators_vectorized(df)
    latest_df = df.groupby('symbol').tail(1).copy()
    
    latest_df['roc_10'] = latest_df['roc_10'].fillna(0)
    latest_df['roc_20'] = latest_df['roc_20'].fillna(0)
    
    # Calculate scores
    roc_score = np.select(
        [
            latest_df['roc_10'] > 5.0,
            latest_df['roc_10'] > 2.0,
            (latest_df['roc_10'] >= -1.0) & (latest_df['roc_10'] <= 2.0),
            latest_df['roc_10'] >= -3.0
        ],
        [100, 80, 50, 35],
        default=10
    )
    
    mfi = latest_df['mfi']
    mfi_score = np.select(
        [
            (mfi > 50) & (mfi < 80),
            (mfi >= 35) & (mfi <= 50),
            (mfi >= 20) & (mfi < 35),
            mfi < 20
        ],
        [90, 50, 35, 10],
        default=40
    )
    
    trend_score = np.select(
        [
            (latest_df['roc_10'] > 0) & (latest_df['roc_20'] > 0),
            (latest_df['roc_10'] > 0) | (latest_df['roc_20'] > 0),
            (latest_df['roc_10'] < 0) & (latest_df['roc_20'] < 0),
            (latest_df['roc_10'] < 0) | (latest_df['roc_20'] < 0)
        ],
        [90, 70, 10, 35],
        default=50
    )
    
    latest_df['score'] = (roc_score * 0.4) + (mfi_score * 0.3) + (trend_score * 0.3)
    latest_df['bucket'] = latest_df['score'].apply(get_bucket)
    
    print("Full database momentum distribution:")
    print(latest_df['bucket'].value_counts())
    
    # Print distinct score values
    print("\nDistinct score values:")
    print(latest_df['score'].value_counts())

if __name__ == "__main__":
    main()
