"""Analyze database tables and data"""
from sqlalchemy import create_engine, text
from config import settings

engine = create_engine(settings.DATABASE_URL.replace('+aiosqlite', ''), connect_args={'check_same_thread': False})

with engine.connect() as conn:
    print("=" * 70)
    print("DATABASE ANALYSIS")
    print("=" * 70)
    
    # 1. NIFTY100_DAILY
    print("\n1. NIFTY100_DAILY (AI Scanner Data - Daily)")
    print("-" * 50)
    r = conn.execute(text("SELECT COUNT(*) FROM nifty100_daily"))
    print(f"   Total records: {r.scalar():,}")
    r = conn.execute(text("SELECT COUNT(DISTINCT symbol) FROM nifty100_daily"))
    print(f"   Unique symbols: {r.scalar()}")
    r = conn.execute(text("SELECT MIN(timestamp), MAX(timestamp) FROM nifty100_daily"))
    row = r.fetchone()
    print(f"   Date range: {row[0]} to {row[1]}")
    
    # 2. STOCK_DATA
    print("\n2. STOCK_DATA (Historical 1-min Data)")
    print("-" * 50)
    r = conn.execute(text("SELECT COUNT(*) FROM stock_data"))
    total = r.scalar()
    print(f"   Total records: {total:,}")
    r = conn.execute(text("SELECT COUNT(DISTINCT symbol) FROM stock_data"))
    print(f"   Unique symbols: {r.scalar()}")
    r = conn.execute(text("SELECT MIN(timestamp), MAX(timestamp) FROM stock_data"))
    row = r.fetchone()
    print(f"   Date range: {row[0]} to {row[1]}")
    
    # By interval using raw SQL
    r = conn.execute(text("SELECT interval, COUNT(*) FROM stock_data GROUP BY interval"))
    print("   By interval:")
    for row in r.fetchall():
        print(f"      {row[0]}: {row[1]:,} records")
    
    # 3. INTRADAY_CANDLES
    print("\n3. INTRADAY_CANDLES (Multi-timeframe)")
    print("-" * 50)
    r = conn.execute(text("SELECT COUNT(*) FROM intraday_candles"))
    total = r.scalar()
    print(f"   Total records: {total:,}")
    r = conn.execute(text("SELECT COUNT(DISTINCT symbol) FROM intraday_candles"))
    print(f"   Unique symbols: {r.scalar()}")
    
    if total > 0:
        r = conn.execute(text("SELECT MIN(timestamp), MAX(timestamp) FROM intraday_candles"))
        row = r.fetchone()
        print(f"   Date range: {row[0]} to {row[1]}")
        
        r = conn.execute(text("SELECT interval, COUNT(*) FROM intraday_candles GROUP BY interval"))
        print("   By interval:")
        for row in r.fetchall():
            print(f"      {row[0]}: {row[1]:,} records")
    
    # List symbols
    print("\n4. SYMBOL LISTS")
    print("-" * 50)
    
    print("\n   NIFTY100_DAILY symbols (200 total):")
    r = conn.execute(text("SELECT DISTINCT symbol FROM nifty100_daily ORDER BY symbol"))
    symbols = [row[0] for row in r.fetchall()]
    print(f"   Count: {len(symbols)}")
    
    print("\n   STOCK_DATA symbols:")
    r = conn.execute(text("SELECT DISTINCT symbol FROM stock_data ORDER BY symbol"))
    symbols = [row[0] for row in r.fetchall()]
    print(f"   Count: {len(symbols)}")
    for s in symbols:
        print(f"   - {s}")
    
    print("\n   INTRADAY_CANDLES symbols:")
    r = conn.execute(text("SELECT DISTINCT symbol FROM intraday_candles ORDER BY symbol"))
    symbols = [row[0] for row in r.fetchall()]
    print(f"   Count: {len(symbols)}")
    for s in symbols:
        print(f"   - {s}")
