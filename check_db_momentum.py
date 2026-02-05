from database import SessionLocal
from models_ml import Nifty100Daily
from sqlalchemy import func
from services.momentum_scanner import MomentumScanner
import pandas as pd

def check_db():
    session = SessionLocal()
    try:
        count = session.query(func.count(Nifty100Daily.id)).scalar()
        print(f"Total rows in Nifty100Daily: {count}")
        
        # Check distinct symbols
        symbols = session.query(Nifty100Daily.symbol).distinct().count()
        print(f"Total distinct symbols: {symbols}")
        
        # Check latest date
        latest = session.query(func.max(Nifty100Daily.timestamp)).scalar()
        print(f"Latest timestamp: {latest}")
        
    finally:
        session.close()

def test_scanner():
    print("\nRunning Momentum Scanner directly...")
    scanner = MomentumScanner()
    try:
        results = scanner.scan_all()
        print(f"Scanner found {len(results)} results.")
        if len(results) == 0:
            print("Scanner returned empty list.")
            print("Troubleshooting: Checking raw dataframe fetch...")
            df = scanner._get_bulk_ohlcv_df()
            print(f"Bulk DF shape: {df.shape}")
            if not df.empty:
                print("Sample data:")
                print(df.head())
                print("Calculating indicators...")
                df_ind = scanner._calculate_indicators_vectorized(df)
                print(f"Indicators DF shape: {df_ind.shape}")
                print(df_ind[['symbol', 'roc_10', 'mfi', 'score']].tail())
    except Exception as e:
        print(f"Scanner error: {e}")

if __name__ == "__main__":
    check_db()
    test_scanner()
