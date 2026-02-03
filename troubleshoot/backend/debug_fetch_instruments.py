import asyncio
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
# DATABASE_URL is async in .env, convert to sync for sqlalchemy
raw_url = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/quantai")
DB_URL = raw_url.replace("+asyncpg", "")

def main():
    engine = create_engine(DB_URL)
    targets = ["MEDANTA", "AMBER", "ANGELONE", "GRSE"]
    
    print(f"Connecting to DB: {DB_URL}")
    with engine.connect() as conn:
        print("Searching for targets in instrument_master...")
        # Note: INDIA VIX might be in a different format or table?
        # Check standard symbols first
        result = conn.execute(text("SELECT symbol, instrument_key FROM instrument_master WHERE symbol IN :targets"), {"targets": tuple(targets)})
        found = {row.symbol: row.instrument_key for row in result}
        
        print("\nFound via DB:")
        for sym, key in found.items():
            print(f'"{sym}", "{key}"')
            
        missing = [t for t in targets if t not in found]
        if missing:
            print(f"\nStill missing in DB: {missing}")
            # Try fuzzy search?
            for m in missing:
                res = conn.execute(text("SELECT symbol, instrument_key FROM instrument_master WHERE symbol ILIKE :pat LIMIT 1"), {"pat": f"%{m}%"})
                row = res.fetchone()
                if row:
                    print(f"Fuzzy match for {m}: {row.symbol} -> {row.instrument_key}")

if __name__ == "__main__":
    main()
