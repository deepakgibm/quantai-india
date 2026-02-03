import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load env
load_dotenv()

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://quantai:quantai_password@localhost:5432/quantai_db")
if "asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
if "postgresql://" in DATABASE_URL and "psycopg2" not in DATABASE_URL:
     DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")

def verify_data():
    print(f"Connecting to database: {DATABASE_URL}")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # 1. Count total symbols in instrument_master
            result = conn.execute(text("SELECT COUNT(*) FROM instrument_master"))
            total_symbols = result.scalar()
            print(f"\nTotal Symbols in Instrument Master: {total_symbols}")

            # 2. Count symbols with data in stock_candle
            print("Checking candle data coverage...")
            query = text("""
                SELECT im.symbol, COUNT(sc.candle_ts) as candle_count, MIN(sc.candle_ts) as start_date, MAX(sc.candle_ts) as end_date
                FROM instrument_master im
                LEFT JOIN stock_candle sc ON im.instrument_id = sc.instrument_id
                GROUP BY im.symbol
            """)
            df = pd.read_sql(query, conn)
            
            symbols_with_data = df[df['candle_count'] > 0]
            symbols_no_data = df[df['candle_count'] == 0]
            recent_data = symbols_with_data[symbols_with_data['end_date'] >= pd.Timestamp('2026-01-01')]
            
            print("-" * 30)
            print(f"Total Symbols: {total_symbols}")
            print(f"Symbols with Recent Data (2026): {len(recent_data)}")
            print("-" * 30)
            sys.stdout.flush()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_data()
