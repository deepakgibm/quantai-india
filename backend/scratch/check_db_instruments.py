import asyncio
from database import SessionLocal
from sqlalchemy import text

async def check():
    db = SessionLocal()
    try:
        # Check table columns
        res = db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public';"))
        tables = [row[0] for row in res]
        print(f"Tables: {tables}")
        
        if "instrument_master" in tables:
            # count
            count = db.execute(text("SELECT count(*) FROM instrument_master;")).fetchone()[0]
            print(f"Total instruments: {count}")
            
            # types/exchanges
            res = db.execute(text("SELECT exchange, count(*) FROM instrument_master GROUP BY exchange;"))
            print("Exchanges:")
            for r in res:
                print(f"  {r[0]}: {r[1]}")
                
            # print some active ones
            res = db.execute(text("SELECT symbol, instrument_key, exchange, is_active FROM instrument_master WHERE is_active = TRUE LIMIT 10;"))
            print("\nActive Instruments Sample:")
            for r in res:
                print(f"  Symbol: {r[0]} | Key: {r[1]} | Exchange: {r[2]} | Active: {r[3]}")
                
            # check if there are option keys
            option_count = db.execute(text("SELECT count(*) FROM instrument_master WHERE instrument_key LIKE '%|%';")).fetchone()[0]
            print(f"\nInstruments with '|' in key: {option_count}")
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(check())
