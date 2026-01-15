import os
import sys
import random
from sqlalchemy import create_engine, text

sys.path.append(os.path.join(os.getcwd(), 'backend'))
from config import settings

SECTORS = ["Financial Services", "Energy", "IT", "Auto", "Pharma"] # Simplified

def simple_populate():
    print(f"Simple Populate: {settings.SYNC_DATABASE_URL}")
    engine = create_engine(settings.SYNC_DATABASE_URL)
    with engine.connect() as conn:
        # 1. Fetch symbols from STOCK_DATA
        print("Fetching symbols from stock_data...")
        try:
            res = conn.execute(text("SELECT DISTINCT symbol FROM stock_data LIMIT 50"))
            symbols = [r[0] for r in res.fetchall()]
            print(f"Got {len(symbols)} symbols from stock_data")
        except Exception as e:
            print(f"Failed to read stock_data: {e}")
            return

        # 2. Update stock_master
        print("Updating stock_master...")
        stmt_update = text("UPDATE stock_master SET sector=:sector, instrument_key=:ikey, is_active=true WHERE symbol=:symbol")
        stmt_insert = text("INSERT INTO stock_master (symbol, sector, instrument_key, is_active, created_at, updated_at) VALUES (:symbol, :sector, :ikey, true, NOW(), NOW())")
        
        updated = 0
        inserted = 0
        
        for sym in symbols:
            sector = random.choice(SECTORS)
            ikey = f"NSE_EQ|{sym}"
            params = {"sector": sector, "ikey": ikey, "symbol": sym}
            
            try:
                res = conn.execute(stmt_update, params)
                if res.rowcount == 0:
                    # Insert
                    conn.execute(stmt_insert, params)
                    inserted += 1
                else:
                    updated += 1
            except Exception as e:
                print(f"Failed for {sym}: {e}")
                # Don't break, continue
        
        conn.commit()
        print(f"Finished. Updated: {updated}, Inserted: {inserted}")

if __name__ == "__main__":
    simple_populate()
