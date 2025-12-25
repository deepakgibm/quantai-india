"""Check database tables and data"""
from sqlalchemy import create_engine, text
from config import settings

engine = create_engine(settings.SYNC_DATABASE_URL)
print(f"Database URL: {settings.SYNC_DATABASE_URL[:50]}...")

with engine.connect() as conn:
    # Check what tables exist
    try:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [r[0] for r in result]
        print(f"\nTables found: {tables}")
    except Exception as e:
        print(f"Error listing tables: {e}")
        # Try PostgreSQL way
        try:
            result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))
            tables = [r[0] for r in result]
            print(f"\nPostgreSQL Tables: {tables}")
        except:
            tables = []
    
    # Check nifty_100_daily
    for table in ['nifty_100_daily', 'stock_data']:
        try:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.fetchone()[0]
            print(f"\n{table}: {count} rows")
            
            if count > 0:
                result = conn.execute(text(f"SELECT DISTINCT symbol FROM {table} LIMIT 10"))
                symbols = [r[0] for r in result]
                print(f"  Sample symbols: {symbols}")
        except Exception as e:
            print(f"\n{table}: Error - {e}")
