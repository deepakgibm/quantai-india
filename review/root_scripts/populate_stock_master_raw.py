import os
import sys
import random
import psycopg2

sys.path.append(os.path.join(os.getcwd(), 'backend'))
from config import settings

SECTORS = ["Financial Services", "Energy", "IT", "Auto", "Pharma"]

def raw_populate():
    print(f"Raw Populate: {settings.SYNC_DATABASE_URL}")
    try:
        conn = psycopg2.connect(settings.SYNC_DATABASE_URL)
        cur = conn.cursor()
        
        # 1. Fetch symbols
        cur.execute("SELECT DISTINCT symbol FROM stock_data LIMIT 50")
        symbols = [r[0] for r in cur.fetchall()]
        print(f"Got {len(symbols)} symbols")
        
        updated = 0
        inserted = 0
        
        for sym in symbols:
            sector = random.choice(SECTORS)
            ikey = f"NSE_EQ|{sym}"
            
            # Update
            cur.execute("UPDATE stock_master SET sector=%s, instrument_key=%s, is_active=true WHERE symbol=%s", (sector, ikey, sym))
            if cur.rowcount == 0:
                try:
                    cur.execute("INSERT INTO stock_master (symbol, company_name, sector, instrument_key, is_active, created_at, updated_at) VALUES (%s, %s, %s, %s, true, NOW(), NOW())", (sym, sym, sector, ikey))
                    inserted += 1
                except Exception as ex:
                    print(f"Insert failed {sym}: {ex}")
                    conn.rollback()
                    continue
            else:
                updated += 1
            
            conn.commit() # Commit each (slow but debugging)
            
        print(f"Done. Upd: {updated}, Ins: {inserted}")
        conn.close()
        
    except Exception as e:
        print(f"Connection/Global Error: {e}")

if __name__ == "__main__":
    raw_populate()
