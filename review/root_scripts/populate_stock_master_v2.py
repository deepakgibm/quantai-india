import os
import sys
import random
from sqlalchemy import create_engine, text

sys.path.append(os.path.join(os.getcwd(), 'backend'))
from config import settings

SECTORS = [
    "Financial Services", "Information Technology", "Auto", "Pharma", 
    "FMCG", "Energy", "Metals", "Consumer Durables", "Telecommunication"
]

def populate_master():
    print(f"Populating stock_master (Upsert): {settings.SYNC_DATABASE_URL}")
    try:
        engine = create_engine(settings.SYNC_DATABASE_URL)
        with engine.connect() as conn:
            
            # Get symbols from stock_data
            result = conn.execute(text("SELECT DISTINCT symbol FROM stock_data"))
            # Limit to 100 for now to ensure speed
            symbols = [row[0] for row in result.fetchall()]
            print(f"Found {len(symbols)} symbols in stock_data")
            
            data_to_insert = []
            for sym in symbols:
                sector = random.choice(SECTORS)
                
                if any(x in sym for x in ['BANK', 'HDFC', 'SBI', 'ICICI']): sector = "Financial Services"
                elif any(x in sym for x in ['TCS', 'INFY', 'WIPRO', 'TECHM', 'HCL']): sector = "Information Technology"
                elif any(x in sym for x in ['AUTO', 'MOTORS', 'TATA', 'MAHINDRA']): sector = "Auto"
                elif any(x in sym for x in ['PHARMA', 'DRREDDY', 'CIPLA', 'DIVIS']): sector = "Pharma"
                elif any(x in sym for x in ['POWER', 'NTPC', 'ONGC', 'BPCL', 'RELIANCE']): sector = "Energy"
                
                instrument_key = f"NSE_EQ|{sym}"
                
                data_to_insert.append({
                    "symbol": sym,
                    "sector": sector,
                    "instrument_key": instrument_key,
                    "is_active": True
                })
            
            # Upsert
            stmt = text("""
                INSERT INTO stock_master (symbol, sector, instrument_key, is_active)
                VALUES (:symbol, :sector, :instrument_key, :is_active)
                ON CONFLICT (symbol) DO UPDATE 
                SET sector = EXCLUDED.sector,
                    instrument_key = EXCLUDED.instrument_key,
                    is_active = EXCLUDED.is_active
            """)
            
            # Execute one by one to isolate errors (slow but safe for 100)
            count = 0
            for item in data_to_insert:
                try:
                    conn.execute(stmt, item)
                    count += 1
                except Exception as ex:
                    print(f"Failed for {item['symbol']}: {ex}")
            
            conn.commit()
            print(f"Upserted {count} rows into stock_master")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    populate_master()
