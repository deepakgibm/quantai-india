"""
Simple Nifty 200 Data Loader using yfinance
Sequential loading - more reliable than parallel
"""

import json
import sys
from pathlib import Path
import yfinance as yf
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from models_ml import Nifty100Daily


def main():
    print("=" * 60)
    print("NIFTY 200 LOADER (Sequential)")
    print("=" * 60)
    
    # Load symbols
    json_path = Path(__file__).parent / "nifty200_instruments.json"
    with open(json_path, 'r') as f:
        data = json.load(f)
    symbols = [item[0] for item in data]
    print(f"📊 Found {len(symbols)} symbols")
    
    # DB connection
    engine = create_engine(
        settings.DATABASE_URL.replace("+aiosqlite", ""),
        connect_args={"check_same_thread": False}
    )
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Check existing symbols
    result = session.execute(text("SELECT DISTINCT symbol FROM nifty100_daily"))
    existing = set(row[0] for row in result.fetchall())
    print(f"📂 Already in DB: {len(existing)} symbols")
    
    # Only load missing ones
    to_load = [s for s in symbols if s not in existing]
    print(f"🔄 To load: {len(to_load)} symbols")
    print()
    
    success = 0
    failed = 0
    total_records = 0
    
    for i, sym in enumerate(to_load, 1):
        try:
            ticker = f"{sym}.NS"
            stock = yf.Ticker(ticker)
            df = stock.history(period="1mo")
            
            if df.empty:
                print(f"[{i:3}/{len(to_load)}] {sym}: No data ⚠️")
                failed += 1
                continue
            
            for idx, row in df.iterrows():
                obj = Nifty100Daily(
                    symbol=sym,
                    timestamp=idx.to_pydatetime().replace(tzinfo=None),
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=int(row['Volume'])
                )
                session.merge(obj)
            
            session.commit()
            print(f"[{i:3}/{len(to_load)}] {sym}: {len(df)} days ✓")
            success += 1
            total_records += len(df)
            
        except Exception as e:
            print(f"[{i:3}/{len(to_load)}] {sym}: Error - {str(e)[:30]} ✗")
            failed += 1
            session.rollback()
    
    session.close()
    
    # Final count
    session2 = Session()
    result = session2.execute(text("SELECT COUNT(DISTINCT symbol) FROM nifty100_daily"))
    final_count = result.scalar()
    session2.close()
    
    print()
    print("=" * 60)
    print("✅ COMPLETE!")
    print(f"   Success: {success}, Failed: {failed}")
    print(f"   Total records added: {total_records}")
    print(f"   Total symbols in DB: {final_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
