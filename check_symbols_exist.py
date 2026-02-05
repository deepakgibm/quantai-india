
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# DB Config
DB_URL = "postgresql://postgres:admin@localhost:5432/quantai"

def check_symbols():
    symbols_to_check = [
        "ZOMATO", "GNFC", "ABORL", "AEGISCHEM", "AMARAJABAT", "ANURAS", 
        "BIRLACORPN", "CENTURYTEX", "CHEMPLASTS", "EDELWEISS", "FINEORG", 
        "GALAXYSURF", "GOCOLORS", "GSFC", "GUJALKALI", "IIFLWAM", "INDIANHUME", 
        "INDIGOPNTS", "JKLAKSHMI", "JKPAPER", "JTEKTINDIA", "KALPATPOWR", 
        "KANSAINER", "ALLCARGO", "TATAMOTORS", "BALAMINES", "DELTACORP", 
        "EPL", "EQUITASBNK", "GARFIBRES", "GRINDWELL", "HATSUN", "ISEC", 
        "JUSTDIAL", "KNRCON", "KRBL"
    ]

    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        # Check against instrument_master
        print(f"Checking {len(symbols_to_check)} symbols in instrument_master...")
        print("-" * 60)
        print(f"{'SYMBOL':<15} | {'STATUS':<10} | {'INSTRUMENT_ID'}")
        print("-" * 60)
        
        found_count = 0
        missing = []
        
        for symbol in symbols_to_check:
            cur.execute("SELECT instrument_id FROM instrument_master WHERE symbol = %s LIMIT 1", (symbol,))
            res = cur.fetchone()
            
            if res:
                print(f"{symbol:<15} | FOUND      | {res[0]}")
                found_count += 1
            else:
                print(f"{symbol:<15} | MISSING    | -")
                missing.append(symbol)
                
        print("-" * 60)
        print(f"Summary: Found {found_count}/{len(symbols_to_check)} symbols.")
        
        if missing:
            print(f"\nMissing Symbols ({len(missing)}):")
            print(", ".join(missing))
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    check_symbols()
