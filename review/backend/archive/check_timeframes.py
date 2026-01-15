"""Check available timeframes in database"""
from sqlalchemy import create_engine, text
from config import settings

engine = create_engine(settings.SYNC_DATABASE_URL)

print("Checking database for available data timeframes...")
print(f"Database: {settings.SYNC_DATABASE_URL[:30]}...")
print()

with engine.connect() as conn:
    # Check Nifty100Daily table
    try:
        result = conn.execute(text("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM nifty_100_daily"))
        row = result.fetchone()
        print(f"nifty_100_daily: {row[0]} rows")
        print(f"  Date range: {row[1]} to {row[2]}")
        
        result = conn.execute(text("SELECT symbol, COUNT(*) as cnt FROM nifty_100_daily GROUP BY symbol LIMIT 5"))
        rows = result.fetchall()
        print(f"  Sample symbols: {[(r[0], r[1]) for r in rows]}")
    except Exception as e:
        print(f"nifty_100_daily: Error - {e}")
    
    print()
    
    # Check stock_data table for different intervals
    try:
        result = conn.execute(text("SELECT interval, COUNT(*) as cnt FROM stock_data GROUP BY interval"))
        rows = result.fetchall()
        print("stock_data intervals:")
        for row in rows:
            print(f"  {row[0]}: {row[1]} rows")
            
        # Check sample for each interval
        for interval in ['5minute', '15minute', '30minute', '1hour', 'day']:
            result = conn.execute(text(f"SELECT DISTINCT symbol FROM stock_data WHERE interval = '{interval}' LIMIT 5"))
            symbols = [r[0] for r in result.fetchall()]
            if symbols:
                print(f"    {interval} symbols: {symbols}")
    except Exception as e:
        print(f"stock_data: Error - {e}")
    
    print()
    
    # Check for RELIANCE specifically
    print("RELIANCE data availability:")
    try:
        # Daily from nifty_100_daily
        result = conn.execute(text("SELECT COUNT(*) FROM nifty_100_daily WHERE symbol = 'RELIANCE'"))
        count = result.fetchone()[0]
        print(f"  nifty_100_daily: {count} rows")
        
        # Check stock_data for all intervals
        result = conn.execute(text("SELECT interval, COUNT(*) FROM stock_data WHERE symbol = 'RELIANCE' GROUP BY interval"))
        for row in result.fetchall():
            print(f"  stock_data ({row[0]}): {row[1]} rows")
    except Exception as e:
        print(f"  Error: {e}")
