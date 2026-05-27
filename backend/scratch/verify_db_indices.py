import asyncio
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from config import settings

def main():
    engine = create_engine(settings.SYNC_DATABASE_URL)
    query = text("""
        SELECT symbol, instrument_key, exchange, is_active 
        FROM instrument_master 
        WHERE symbol ILIKE 'nifty%' OR symbol ILIKE 'bank%'
        LIMIT 20
    """)
    with engine.connect() as conn:
        res = conn.execute(query).fetchall()
        print("Matching symbol rows in DB:")
        for r in res:
            print(f"Symbol: {r[0]} | Key: {r[1]} | Exch: {r[2]} | Active: {r[3]}")

if __name__ == "__main__":
    main()
