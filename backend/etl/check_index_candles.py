
import os
import psycopg2
from datetime import datetime, timedelta

# Get DB URL from env or default - LOCALHOST
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/quantai")
if "+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

def check_candle_data():
    print(f"Connecting to {DATABASE_URL}")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        indices = ["NIFTY 50", "BANK NIFTY", "INDIA VIX"]
        
        print(f"\nChecking STOCK_CANDLE data for: {indices}")
        print("="*60)
        
        for symbol in indices:
            print(f"\n--- {symbol} ---")
            
            # 1. Get Instrument ID
            cur.execute("SELECT instrument_id, symbol FROM instrument_master WHERE symbol = %s", (symbol,))
            row = cur.fetchone()
            
            if not row:
                print(f"  [MISSING] Not found in instrument_master!")
                continue
                
            instrument_id = row[0]
            print(f"  Instrument ID: {instrument_id}")
            
            # 2. Check stock_candle (New Schema) - Breakdown by Timeframe
            cur.execute("""
                SELECT timeframe, COUNT(*), MAX(candle_ts)
                FROM stock_candle
                WHERE instrument_id = %s
                GROUP BY timeframe
                ORDER BY timeframe
            """, (instrument_id,))
            
            rows = cur.fetchall()
            if rows:
                print("  Data by Timeframe:")
                for r in rows:
                    print(f"    TF {r[0]} ({'1d' if r[0]==1440 else str(r[0])+'m'}): {r[1]} rows, Last: {r[2]}")
            else:
                print("  [EMPTY] No data in stock_candle")

            # Check legacy table just in case
                # Check legacy table
                cur.execute("""
                    SELECT COUNT(*) FROM stock_candles 
                    WHERE symbol = %s
                """, (symbol,))
                legacy_count = cur.fetchone()[0]
                print(f"  Rows in legacy stock_candles: {legacy_count}")

        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_candle_data()
