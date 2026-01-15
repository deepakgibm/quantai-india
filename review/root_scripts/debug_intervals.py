import os
import sys
from sqlalchemy import create_engine, text

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from config import settings

def check_intervals():
    print(f"Checking Intervals in DB: {settings.SYNC_DATABASE_URL}")
    try:
        engine = create_engine(settings.SYNC_DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT DISTINCT \"interval\" FROM stock_data"))
            intervals = [row[0] for row in result.fetchall()]
            print(f"Distinct Intervals: {intervals}")
            
            # Check counts for each
            for interval in intervals:
                count = conn.execute(text("SELECT COUNT(*) FROM stock_data WHERE \"interval\" = :interval"), {"interval": interval}).scalar()
                print(f"Interval '{interval}': {count} rows")

    except Exception as e:
        print(f"❌ DB Check failed: {e}")

if __name__ == "__main__":
    check_intervals()
